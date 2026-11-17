"""Staging-only POC API: validates Excel A-K and returns row statuses. NEVER writes DB."""
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Flask, jsonify, request

app = Flask(__name__)
ALLOWED_ORIGIN = os.getenv('ALLOWED_ORIGIN', 'https://meldanophia.github.io')
FIELDS = ['nomor_sk','transporter','asal_kota','tujuan_kota','jenis_kendaraan',
          'tipe_muatan','tipe_harga','start_date','price','tkbm','valid_date']
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# Nullable VARCHAR; strict literal '[YYYY-MM-DD,YYYY-MM-DD]' format.
RANGE_RE = re.compile(r'^\[(\d{4}-\d{2}-\d{2}),(\d{4}-\d{2}-\d{2})\]$')

@app.after_request
def cors(response):
    if request.headers.get('Origin') == ALLOWED_ORIGIN:
        response.headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Vary'] = 'Origin'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/poc/health')
def health():
    return jsonify(status='ok', service='mostrans-poc-03', database_used=False)

@app.route('/poc/validate',methods=['POST','OPTIONS'])
def validate():
    if request.method == 'OPTIONS':
        return '',204
    if request.content_length is None or request.content_length > 1_500_000:
        return jsonify(error='Payload missing or too large'),413
    data = request.get_json(silent=True)
    if not isinstance(data,dict) or data.get('operation') != 'POC_VALIDATE_INACTIVE_PRICE_NO_SQL':
        return jsonify(error='Operation POC tidak sesuai'),400
    rows = data.get('rows')
    if not isinstance(rows,list) or not 1 <= len(rows) <= 1000:
        return jsonify(error='Jumlah row harus 1 sampai 1000'),400
    results = []
    seen = set()
    for item in rows:
        if not isinstance(item,dict):
            return jsonify(error='Setiap row harus berupa JSON object'),400
        row_id=item.get('row_id')
        sheet_row=item.get('sheet_row')
        if not isinstance(row_id,str) or not row_id or row_id in seen or not isinstance(sheet_row,int) or sheet_row < 2:
            return jsonify(error='row_id unik dan sheet_row >= 2 diperlukan'),400
        seen.add(row_id)
        errors=[]
        for field in FIELDS[:7]:
            if not isinstance(item.get(field),str) or not item[field].strip():
                errors.append(f'{field}: wajib diisi')
        if not isinstance(item.get('start_date'),str) or not DATE_RE.fullmatch(item['start_date']):
            errors.append('start_date: wajib YYYY-MM-DD')
        else:
            try: date.fromisoformat(item['start_date'])
            except ValueError: errors.append('start_date: tanggal tidak valid')
        for field in ['price','tkbm']:
            value=item.get(field)
            try:
                if isinstance(value,bool) or value is None or str(value).strip()=='': raise InvalidOperation()
                amount=Decimal(str(value))
                if not amount.is_finite() or amount < 0: raise InvalidOperation()
            except (InvalidOperation,ValueError,TypeError):
                errors.append(f'{field}: harus angka >= 0')
        raw_valid_date = item.get('valid_date')
        # Empty cells and JSON null mean SQL NULL, never an empty string.
        valid_date = None if raw_valid_date is None or raw_valid_date == '' else raw_valid_date
        if valid_date is not None:
            if not isinstance(valid_date, str):
                errors.append('valid_date: harus string atau null')
            else:
                match = RANGE_RE.fullmatch(valid_date)
                if not match:
                    errors.append('valid_date: format harus [YYYY-MM-DD,YYYY-MM-DD] tanpa spasi')
                else:
                    try:
                        start = date.fromisoformat(match.group(1))
                        end = date.fromisoformat(match.group(2))
                        if start > end:
                            errors.append('valid_date: tanggal awal lebih besar dari akhir')
                    except ValueError:
                        errors.append('valid_date: tanggal tidak valid')
        results.append({
            'row_id':row_id,'sheet_row':sheet_row,
            'status':'valid' if not errors else 'invalid',
            'error_message':'; '.join(errors),
            'valid_date':valid_date
        })
    return jsonify(status='validated', database_used=False, total_rows=len(results),
                   valid_rows=sum(r['status']=='valid' for r in results),
                   invalid_rows=sum(r['status']=='invalid' for r in results),results=results)

if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.getenv('PORT','6077')),debug=False)
