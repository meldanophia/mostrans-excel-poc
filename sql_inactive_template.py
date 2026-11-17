"""REFERENCE ONLY: no database execution in POC 03.1.

PostgreSQL mt_harga_transporter.valid_date is VARCHAR, nullable.
The value must match exactly '[YYYY-MM-DD,YYYY-MM-DD]', or SQL NULL.
Lookup IDs on the backend and pass the `valid_date` parameter as a string or None.
"""

SQL_INACTIVE_HARGA_TRANSPORTER = """
UPDATE public.mt_harga_transporter AS h
SET active = 'I',
    status = 6,
    inactive_date = NOW()
WHERE h.transporter_id = %(transporter_id)s
  AND h.nomor_sk LIKE %(nomor_sk_pattern)s
  AND h.asal_id = %(asal_id)s
  AND h.tujuan_id = %(tujuan_id)s
  AND h.jenis_kendaraan_id = %(jenis_kendaraan_id)s
  AND h.tipe_muatan = %(tipe_muatan)s
  AND h.tipe_harga_id = %(tipe_harga_id)s
  AND h.start_date = %(start_date)s
  AND h.valid_date IS NOT DISTINCT FROM %(valid_date)s::varchar
  AND h.active = 'A'
RETURNING h.id;
"""

# SQL NULL is matched with SQL NULL. Empty string is NOT equivalent to NULL:
# normalize blank Excel K cells to Python None before passing SQL parameters.
# The active='A' filter was introduced in POC 03, and should be confirmed
# against business requirements before production use.
# The existing nomor_sk LIKE pattern is kept for parity; escape %, _ and
# backslashes, or use equality after confirming business rules.
# A zero-row RETURNING result is not a successful update.
