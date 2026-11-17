"""POC05 dry-run and guarded staging execution. Imported by flask_poc_api.py.
Execution requires explicit migration, env flag, staging environment, token, preview proof.
"""
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from flask import jsonify, request
from poc05_sql import SELECT_MATCHES, UPDATE_ONE, params

MAX_EXECUTE_ROWS=50
PREVIEW_EXPIRY_SECONDS=600

def register_poc05(app, helpers):
    validate_row=helpers['validate_row']
    read_mapping=helpers['read_mapping']
    load_master_maps=helpers['load_master_maps']
    LOOKUPS=helpers['LOOKUPS']
    psycopg=helpers['psycopg']
    parsed_request=helpers['parsed_request']

    def require_token():
        secret=os.getenv('POC_LOOKUP_TOKEN','')
        supplied=request.headers.get('X-POC-Token','')
        return len(secret)>=24 and hmac.compare_digest(secret,supplied)

    def checksum(rows):
        return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

    def proof_payload(rows, results, issued):
        return {'digest':checksum(rows),'targets':{r['row_id']:r.get('target_id') for r in results},'issued':issued}

    def sign_proof(obj):
        secret=os.getenv('POC_PREVIEW_SECRET','')
        if len(secret)<32: raise ValueError('POC_PREVIEW_SECRET minimal 32 karakter wajib ada')
        canonical=json.dumps(obj,sort_keys=True,separators=(',',':'))
        sig=hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).hexdigest()
        return {'payload':obj,'signature':sig}

    def verify_proof(proof,rows):
        if not isinstance(proof,dict) or not isinstance(proof.get('payload'),dict):
            raise ValueError('Proof dry-run tidak ada')
        expected=sign_proof(proof['payload'])['signature']
        if not isinstance(proof.get('signature'),str) or not hmac.compare_digest(proof['signature'],expected):
            raise ValueError('Proof tidak valid')
        payload=proof['payload']
        if payload.get('digest')!=checksum(rows): raise ValueError('Input Excel berubah sejak dry-run')
        issued=payload.get('issued')
        if type(issued) is not int or issued>time.time()+15 or time.time()-issued>PREVIEW_EXPIRY_SECONDS:
            raise ValueError('Dry-run kedaluwarsa; ulangi')
        return payload['targets']

    def resolved_ids(row,maps):
        ids={};errors=[]
        for field,(group,key) in LOOKUPS.items():
            name=row.get(field)
            found=maps[group].get(name.strip(),set()) if isinstance(name,str) else set()
            if len(found)==1: ids[key]=next(iter(found))
            else:
                errors.append(f'{field}: master '+('tidak ditemukan' if not found else 'ambigu'))
        return ids,errors

    def build_preview(rows,conn):
        conf=read_mapping()
        maps=load_master_maps(conn,conf,rows)
        results=[]
        with conn.cursor() as cur:
            for row in rows:
                valid=validate_row(row)
                errors=[] if valid['status']=='valid' else [valid['error_message']]
                ids,lookup_errors=resolved_ids(row,maps)
                errors.extend(lookup_errors)
                entry={'row_id':row['row_id'],'sheet_row':row['sheet_row'],
                       'status':'invalid' if errors else 'ready',
                       'target_id':None,'matched_count':0,
                       'ids':ids,'error_message':'; '.join(errors)}
                if not errors:
                    cur.execute(SELECT_MATCHES,params(row,ids))
                    targets=[r[0] for r in cur.fetchall()]
                    entry['matched_count']=len(targets) if len(targets)<2 else '2+'
                    if len(targets)==1:
                        entry['target_id']=targets[0]
                    elif not targets:
                        entry['status']='not_found'
                        entry['error_message']='Tidak ditemukan harga aktif yang cocok'
                    else:
                        entry['status']='ambiguous'
                        entry['error_message']='Lebih dari satu harga aktif cocok; UPDATE diblokir'
                results.append(entry)
        return results

    @app.route('/poc/price-preview',methods=['POST','OPTIONS'])
    def price_preview():
        if request.method=='OPTIONS': return '',204
        if not require_token(): return jsonify(error='Token POC tidak valid'),401
        try:
            data=request.get_json(silent=True)
            if not isinstance(data,dict) or data.get('operation')!='POC_PRICE_DRY_RUN':
                return jsonify(error='Operation dry-run tidak valid'),400
            rows=parsed_request()
            if psycopg is None: raise ValueError('psycopg belum terinstall')
            url=os.getenv('DATABASE_URL')
            if not url: raise ValueError('DATABASE_URL belum diatur')
            with psycopg.connect(url,connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute('SET TRANSACTION READ ONLY')
                    cur.execute("SET LOCAL statement_timeout = '15000ms'")
                result=build_preview(rows,conn)
            token=sign_proof(proof_payload(rows,result,int(time.time())))
            return jsonify(status='dry_run_completed',database_written=False,
                total_rows=len(result),ready_rows=sum(r['status']=='ready' for r in result),
                blocked_rows=sum(r['status']!='ready' for r in result),
                results=result,preview_proof=token)
        except Exception as exc:
            app.logger.exception('POC05 preview failed')
            return jsonify(error=f'Dry-run gagal: {type(exc).__name__}. Periksa log Flask.'),503

    @app.route('/poc/price-execute',methods=['POST','OPTIONS'])
    def price_execute():
        if request.method=='OPTIONS': return '',204
        if not require_token(): return jsonify(error='Token POC tidak valid'),401
        if not (os.getenv('POC_ENVIRONMENT','').lower()=='staging' and
                os.getenv('ENABLE_PRICE_UPDATE','false').lower()=='true'):
            return jsonify(error='Execute terkunci. Hanya staging dengan ENABLE_PRICE_UPDATE=true.'),403
        # Never allow DB writes via a public Quick Tunnel; staging execute requires
        # a separately authenticated internal HTTPS deployment.
        allowed_host=os.getenv('POC_EXECUTE_ALLOWED_HOST','').strip().lower()
        if (not allowed_host or request.host.lower()!=allowed_host or
                request.host.lower().endswith('.trycloudflare.com')):
            return jsonify(error='Execute hanya melalui HTTPS host internal terdaftar, bukan Quick Tunnel.'),403
        try:
            body=request.get_json(silent=True)
            if not isinstance(body,dict) or body.get('operation')!='POC_PRICE_EXECUTE' or body.get('confirm')!='EXECUTE_STAGING':
                return jsonify(error='Konfirmasi execute staging tidak sesuai'),400
            rows=parsed_request()
            if len(rows)>MAX_EXECUTE_ROWS: return jsonify(error='Execute POC maksimal 50 row per request'),400
            job_key=body.get('job_key')
            if not isinstance(job_key,str) or len(job_key)>100 or len(job_key)<16:
                return jsonify(error='job_key stabil minimal 16 karakter diperlukan'),400
            targets=verify_proof(body.get('preview_proof'),rows)
            if psycopg is None: raise ValueError('psycopg belum terinstall')
            url=os.getenv('DATABASE_URL')
            if not url: raise ValueError('DATABASE_URL belum diatur')
            # Each row committed together with durable idempotency log.
            results=[]
            for row in rows:
                digest=checksum([row])
                with psycopg.connect(url,connect_timeout=5) as conn:
                    try:
                        with conn.transaction():
                            with conn.cursor() as cur:
                                cur.execute("SET LOCAL statement_timeout='15000ms'")
                                cur.execute('''INSERT INTO public.poc_price_execution_log
                                    (job_key,row_id,input_digest,status)
                                    VALUES (%s,%s,%s,'processing')
                                    ON CONFLICT (job_key,row_id) DO NOTHING RETURNING row_id''',
                                    (job_key,row['row_id'],digest))
                                owned=cur.fetchone() is not None
                                if not owned:
                                    cur.execute('SELECT input_digest,status,target_id,error_message FROM public.poc_price_execution_log WHERE job_key=%s AND row_id=%s',
                                                (job_key,row['row_id']))
                                    old=cur.fetchone()
                                    if not old or old[0]!=digest:
                                        raise ValueError('Idempotency key telah digunakan dengan input berbeda')
                                    results.append({'row_id':row['row_id'],'status':old[1],
                                                    'target_id':old[2],'error_message':old[3] or '', 'replayed':True})
                                    continue
                                target=targets.get(row['row_id'])
                                if target is None:
                                    state='skipped'; message='Dry-run tidak READY'; done_id=None
                                else:
                                    # Revalidate mapping each time, and require original target to remain a unique match.
                                    preview=build_preview([row],conn)[0]
                                    if preview['status']!='ready' or preview['target_id']!=target:
                                        state='stale'; message='Harga berubah sejak dry-run; tidak diupdate';done_id=None
                                    else:
                                        cur.execute(UPDATE_ONE,params(row,preview['ids'],target))
                                        updated=cur.fetchone()
                                        if updated:
                                            state='success';done_id=updated[0];message=''
                                        else:
                                            state='stale';done_id=None;message='Tidak ada row terupdate (mungkin sudah berubah)'
                                cur.execute('''UPDATE public.poc_price_execution_log
                                    SET status=%s,target_id=%s,error_message=%s,finished_at=NOW()
                                    WHERE job_key=%s AND row_id=%s''',
                                    (state,done_id,message,job_key,row['row_id']))
                                results.append({'row_id':row['row_id'],'status':state,
                                                'target_id':done_id,'error_message':message,'replayed':False})
                    except Exception as exc:
                        app.logger.exception('Row update failed: %s',row['row_id'])
                        # Record failure independently; row UPDATE and processing marker are rolled back.
                        message=f'Failed: {type(exc).__name__}; lihat Flask log'
                        with conn.transaction():
                            with conn.cursor() as cur:
                                cur.execute('''INSERT INTO public.poc_price_execution_log
                                  (job_key,row_id,input_digest,status,error_message,finished_at)
                                  VALUES (%s,%s,%s,'failed',%s,NOW())
                                  ON CONFLICT (job_key,row_id) DO NOTHING''',
                                  (job_key,row['row_id'],digest,message))
                        results.append({'row_id':row['row_id'],'status':'failed',
                                        'target_id':None,'error_message':message,'replayed':False})
            return jsonify(status='execute_completed',total_rows=len(results),
                           success_rows=sum(x['status']=='success' for x in results),results=results)
        except (ValueError,KeyError,TypeError) as exc:
            return jsonify(error=str(exc)),400
        except Exception:
            app.logger.exception('POC05 execute failure')
            return jsonify(error='Execute gagal; periksa Flask log'),503
