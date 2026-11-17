"""POC04: Excel A-K validation + READ-ONLY PostgreSQL master lookup.
NO UPDATE/INSERT/DELETE; no execution of spreadsheet-provided SQL.
This demo is unauthenticated: use exclusively with staging and non-sensitive data.
"""
import json
import hmac
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, jsonify, request
from poc05_extension import register_poc05
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None
    sql = None

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1_500_000
ALLOWED_ORIGIN = os.getenv('ALLOWED_ORIGIN', 'https://meldanophia.github.io')
FIELDS = ['nomor_sk','transporter','asal_kota','tujuan_kota','jenis_kendaraan',
          'tipe_muatan','tipe_harga','start_date','price','tkbm','valid_date']
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
RANGE_RE = re.compile(r'^\[(\d{4}-\d{2}-\d{2}),(\d{4}-\d{2}-\d{2})\]$')
IDENT = re.compile(r'^[a-z_][a-z0-9_]*$', re.I)
# Uses existing known Excel mappings, but SQL tables/columns must be verified for YOUR DB.
LOOKUPS = {
    'transporter': ('transporter', 'transporter_id'),
    'asal_kota': ('kota', 'asal_kota_id'),
    'tujuan_kota': ('kota', 'tujuan_kota_id'),
    'jenis_kendaraan': ('jenis_kendaraan', 'jenis_kendaraan_id'),
    'tipe_harga': ('tipe_harga', 'tipe_harga_id'),
}

@app.after_request
def cors(response):
    if request.headers.get('Origin') == ALLOWED_ORIGIN:
        response.headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-POC-Token'
        response.headers['Vary'] = 'Origin'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/poc/health')
def health():
    return jsonify(status='ok', service='mostrans-poc-04', lookup_configured=bool(os.getenv('DATABASE_URL')), db_writes_enabled=False)


def parsed_request():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('operation') not in (
        'POC_VALIDATE_INACTIVE_PRICE_NO_SQL','POC_LOOKUP_INACTIVE_PRICE_READ_ONLY','POC_PRICE_DRY_RUN','POC_PRICE_EXECUTE'):
        raise ValueError('Operation POC tidak sesuai')
    rows = data.get('rows')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError('Jumlah row harus 1 sampai 1000')
    seen = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError('Setiap row harus JSON object')
        row_id, sheet_row = item.get('row_id'), item.get('sheet_row')
        if (not isinstance(row_id, str) or not row_id or row_id in seen or
                type(sheet_row) is not int or sheet_row < 2):
            raise ValueError('row_id unik dan sheet_row >= 2 diperlukan')
        seen.add(row_id)
    return rows


def validate_row(item):
    errors=[]
    for field in FIELDS[:7]:
        if not isinstance(item.get(field),str) or not item[field].strip():
            errors.append(f'{field}: wajib diisi')
    start_date=item.get('start_date')
    if not isinstance(start_date,str) or not DATE_RE.fullmatch(start_date):
        errors.append('start_date: wajib YYYY-MM-DD')
    else:
        try: date.fromisoformat(start_date)
        except ValueError: errors.append('start_date: tanggal tidak valid')
    for field in ('price','tkbm'):
        value=item.get(field)
        try:
            if isinstance(value,bool) or value is None or str(value).strip()=='':
                raise InvalidOperation()
            amount=Decimal(str(value))
            if not amount.is_finite() or amount < 0: raise InvalidOperation()
        except (InvalidOperation,ValueError,TypeError):
            errors.append(f'{field}: harus angka >= 0')
    raw=item.get('valid_date')
    valid_date=None if raw is None or raw=='' else raw
    if valid_date is not None:
        if not isinstance(valid_date,str):
            errors.append('valid_date: harus string atau null')
        else:
            match=RANGE_RE.fullmatch(valid_date)
            if not match:
                errors.append('valid_date: format harus [YYYY-MM-DD,YYYY-MM-DD] tanpa spasi')
            else:
                try:
                    lo=date.fromisoformat(match.group(1))
                    hi=date.fromisoformat(match.group(2))
                    if lo>hi: errors.append('valid_date: tanggal awal lebih besar dari akhir')
                except ValueError: errors.append('valid_date: tanggal tidak valid')
    return {'row_id':item['row_id'], 'sheet_row':item['sheet_row'],
            'status':'valid' if not errors else 'invalid',
            'error_message':'; '.join(errors), 'valid_date':valid_date}


def results_response(results, **extras):
    return jsonify(status='validated', total_rows=len(results),
                   valid_rows=sum(x['status']=='valid' for x in results),
                   invalid_rows=sum(x['status']=='invalid' for x in results),
                   results=results, **extras)

@app.route('/poc/validate', methods=['POST','OPTIONS'])
def validate():
    if request.method=='OPTIONS': return '',204
    try: rows=parsed_request()
    except ValueError as exc: return jsonify(error=str(exc)),400
    return results_response([validate_row(item) for item in rows],database_used=False)


def read_mapping():
    filepath=Path(os.getenv('MASTER_LOOKUP_CONFIG', 'master_lookup.json').strip())
    if not filepath.is_absolute():
        filepath=BASE_DIR / filepath
    config=json.loads(filepath.read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError('root konfigurasi master lookup harus JSON object')
    for name in ('transporter','kota','jenis_kendaraan','tipe_harga'):
        entry=config.get(name)
        if not isinstance(entry,dict): raise ValueError(f'mapping {name} belum diisi')
        for key in ('schema','table','id_column','name_column'):
            value=entry.get(key)
            if not isinstance(value,str) or not IDENT.fullmatch(value):
                raise ValueError(f'mapping {name}.{key} harus identifier PostgreSQL valid')
    return config


def load_master_maps(conn, config, rows):
    master_maps={}
    for group in ('transporter','kota','jenis_kendaraan','tipe_harga'):
        conf=config[group]
        fields=('transporter',) if group=='transporter' else (
            ('asal_kota','tujuan_kota') if group=='kota' else (group,))
        names=sorted({r.get(field).strip() for r in rows for field in fields
                      if isinstance(r.get(field),str) and r.get(field).strip()})
        masters={}
        if names:
            # Identifiers come exclusively from explicit local config, not user input.
            statement=sql.SQL('SELECT {}, {} FROM {}.{} WHERE {} = ANY(%s)').format(
                sql.Identifier(conf['id_column']),sql.Identifier(conf['name_column']),
                sql.Identifier(conf['schema']),sql.Identifier(conf['table']),
                sql.Identifier(conf['name_column']))
            with conn.cursor() as cur:
                cur.execute(statement,(names,))
                for id_value, label in cur.fetchall():
                    key=str(label)
                    masters.setdefault(key,set()).add(id_value)
        master_maps[group]=masters
    return master_maps

@app.route('/poc/master-lookup', methods=['POST','OPTIONS'])
def master_lookup():
    if request.method=='OPTIONS': return '',204
    try: rows=parsed_request()
    except ValueError as exc: return jsonify(error=str(exc)),400
    if request.get_json().get('operation')!='POC_LOOKUP_INACTIVE_PRICE_READ_ONLY':
        return jsonify(error='Operation lookup tidak sesuai'),400
    expected_token=os.getenv('POC_LOOKUP_TOKEN','')
    actual_token=request.headers.get('X-POC-Token','')
    if len(expected_token)<24 or not hmac.compare_digest(expected_token,actual_token):
        return jsonify(error='Akses lookup ditolak. Set POC_LOOKUP_TOKEN di Flask dan isi token pada task pane.'),401
    if psycopg is None:
        return jsonify(error='Install psycopg[binary] terlebih dahulu'),503
    database_url=os.getenv('DATABASE_URL')
    if not database_url:
        return jsonify(error='DATABASE_URL belum diset. Gunakan DB staging read-only.'),503
    try: config=read_mapping()
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as exc:
        return jsonify(error=f'Konfigurasi master lookup tidak valid: {exc}'),503
    try:
        # PostgreSQL READ ONLY + short timeout. This endpoint never writes DB.
        with psycopg.connect(database_url, connect_timeout=5, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL statement_timeout = '10000ms'")
            master_maps=load_master_maps(conn,config,rows)
    except Exception:
        app.logger.exception('POC master lookup failed')
        return jsonify(error='Lookup database gagal. Periksa koneksi, hak SELECT, dan mapping pada log Flask.'),503
    results=[]
    for item in rows:
        record=validate_row(item)
        ids={}
        errors=[] if record['status']=='valid' else [record['error_message']]
        for field, (group, outfield) in LOOKUPS.items():
            label=item.get(field)
            if not isinstance(label,str) or not label.strip():
                ids[outfield]=None
                continue
            matches=master_maps[group].get(label.strip(),set())
            if len(matches)==1:
                ids[outfield]=next(iter(matches))
            elif not matches:
                ids[outfield]=None
                errors.append(f'{field}: master tidak ditemukan ({label.strip()})')
            else:
                ids[outfield]=None
                errors.append(f'{field}: nama master ambigu ({label.strip()})')
        record['ids']=ids
        record['status']='resolved' if not errors else 'lookup_failed'
        record['error_message']='; '.join(e for e in errors if e)
        results.append(record)
    return jsonify(status='lookup_completed',database_used=True,db_writes_enabled=False,
                   total_rows=len(results),resolved_rows=sum(x['status']=='resolved' for x in results),
                   failed_rows=sum(x['status']=='lookup_failed' for x in results),results=results)

register_poc05(app, {'validate_row':validate_row,'read_mapping':read_mapping,
    'load_master_maps':load_master_maps,'LOOKUPS':LOOKUPS,
    'psycopg':psycopg,'parsed_request':parsed_request})

if __name__=='__main__':
    config_path = Path(os.getenv('MASTER_LOOKUP_CONFIG', 'master_lookup.json').strip())
    if not config_path.is_absolute():
        config_path = BASE_DIR / config_path
    print('[POC04] .env path:', BASE_DIR / '.env')
    print('[POC04] .env exists:', (BASE_DIR / '.env').is_file())
    print('[POC04] master config path:', config_path)
    print('[POC04] master config exists:', config_path.is_file())
    print('[POC04] DATABASE_URL configured:', bool(os.getenv('DATABASE_URL')))
    print('[POC04] POC_LOOKUP_TOKEN configured:', len(os.getenv('POC_LOOKUP_TOKEN', '')) >= 24)
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '6077')), debug=False)

