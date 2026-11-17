"""SQL controlled by backend only; never execute SQL originating from Excel."""
# Valid date is VARCHAR in the actual mt_harga_transporter table.
# Escape %, _, and backslash so the user's SK is always treated literally in LIKE.
SELECT_MATCHES = """
SELECT id
FROM public.mt_harga_transporter
WHERE transporter_id = %(transporter_id)s
  AND nomor_sk LIKE %(nomor_sk_pattern)s ESCAPE E'\\\\'
  AND asal_id = %(asal_kota_id)s
  AND tujuan_id = %(tujuan_kota_id)s
  AND jenis_kendaraan_id = %(jenis_kendaraan_id)s
  AND tipe_muatan = %(tipe_muatan)s
  AND tipe_harga_id = %(tipe_harga_id)s
  AND start_date = %(start_date)s::date
  AND valid_date IS NOT DISTINCT FROM %(valid_date)s::varchar
  AND active = 'A'
ORDER BY id
LIMIT 2
"""
UPDATE_ONE = """
UPDATE public.mt_harga_transporter
SET active = 'I', status = 6, inactive_date = NOW()
WHERE id = %(target_id)s
  AND transporter_id = %(transporter_id)s
  AND nomor_sk LIKE %(nomor_sk_pattern)s ESCAPE E'\\\\'
  AND asal_id = %(asal_kota_id)s
  AND tujuan_id = %(tujuan_kota_id)s
  AND jenis_kendaraan_id = %(jenis_kendaraan_id)s
  AND tipe_muatan = %(tipe_muatan)s
  AND tipe_harga_id = %(tipe_harga_id)s
  AND start_date = %(start_date)s::date
  AND valid_date IS NOT DISTINCT FROM %(valid_date)s::varchar
  AND active = 'A'
RETURNING id
"""
def params(row, ids, target_id=None):
    nomor = row['nomor_sk'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
    return {**ids,'nomor_sk_pattern':f'%{nomor}%',
            'tipe_muatan':row['tipe_muatan'], 'start_date':row['start_date'],
            'valid_date':row.get('valid_date'), 'target_id':target_id}
