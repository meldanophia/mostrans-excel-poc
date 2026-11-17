# Mostrans Excel POC 04 — PostgreSQL Master Lookup (READ ONLY)

## Tujuan dan batas aman

- Menjaga fungsi POC03.2: Baca A–K, validasi tanpa database, write-back status AF–AH.
- Tambah endpoint `POST /poc/master-lookup`: **hanya SELECT** ke PostgreSQL staging.
- Cocokkan nama master dengan nilai exact (case-sensitive, trim kanan/kiri) seperti map Apps Script. Nama yang tidak ada atau ambigu dianggap gagal.
- Tambah tombol Office Add-in untuk tulis hasil ID ke **Z:AD** dan status/error ke **AF:AH**.
- **Tidak ada SQL UPDATE/INSERT/DELETE harga, tidak ada auto-hapus baris, tidak mengubah kolom AE.**
- `valid_date` tetap VARCHAR, opsional, dikirim `null` jika kosong. Format input jika diisi `[YYYY-MM-DD,YYYY-MM-DD]`.
- Add-in harus dibuka di **workbook POC / salinan**, karena Z:AD menjadi kolom output; jika berisi ID lama yang berbeda, penulisan otomatis dibatalkan.

## 1. Ketahui nama tabel master PostgreSQL yang benar

Kode Apps Script awal membaca master dari spreadsheet lain, jadi nama tabel `jenis_kendaraan` dan `tipe_harga` pada PostgreSQL belum dapat dipastikan. Jangan menyalin nama tabel contoh tanpa memverifikasi.

Jalankan query diagnosis berikut di database staging:

```sql
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
       table_name ILIKE '%transporter%'
    OR table_name ILIKE '%kota%'
    OR table_name ILIKE '%kendaraan%'
    OR table_name ILIKE '%harga%'
  )
  AND (column_name = 'id' OR column_name ILIKE '%nama%' OR column_name ILIKE '%jenis%' OR column_name ILIKE '%tipe%')
ORDER BY table_name, ordinal_position;
```

Copy `master_lookup.example.json` menjadi `master_lookup.json`, lalu perbaiki nilai `schema`, `table`, `id_column`, `name_column` sesuai tabel sungguhan. Nama pada contoh transporter/kota adalah kandidat berdasarkan diskusi sebelumnya; **tetap verifikasi**. Jangan commit `master_lookup.json` ke repository publik bila memuat detail internal yang sensitif.

## 2. Siapkan environment Windows

Buka terminal pada folder POC04:

```powershell
py -m pip install -r requirements.txt
$env:DATABASE_URL = 'postgresql://readonly_user:YOUR_PASSWORD@STAGING_HOST:5432/YOUR_DATABASE?sslmode=require'
$env:MASTER_LOOKUP_CONFIG = 'master_lookup.json'
$env:POC_LOOKUP_TOKEN = 'GANTI_DENGAN_TOKEN_ACAK_MINIMAL_24_KARAKTER'
py flask_poc_api.py
```

**Command Prompt (CMD)** dapat menggunakan `set DATABASE_URL=...`, `set MASTER_LOOKUP_CONFIG=...`, dan `set POC_LOOKUP_TOKEN=...` (bukan `$env:`).

Gunakan akun PostgreSQL yang punya izin `CONNECT`, `USAGE` schema master, dan hanya `SELECT` untuk empat tabel master. Backend tambahan menjalankan `SET TRANSACTION READ ONLY` dan `statement_timeout` sebagai pertahanan tambahan. Jangan gunakan akun DBA atau akun production yang punya izin update.

Contoh grant yang dikerjakan DBA sesuai nama tabel actual:

```sql
-- Contoh saja; ganti nama tabel sesuai master_lookup.json
GRANT CONNECT ON DATABASE nama_staging_db TO poc_master_reader;
GRANT USAGE ON SCHEMA public TO poc_master_reader;
GRANT SELECT ON public.mt_master_transporter, public.mt_master_kota TO poc_master_reader;
-- Tambahkan GRANT SELECT pada tabel jenis kendaraan dan tipe harga yang benar.
```

Contoh ini tidak membuat role; role harus disiapkan DBA. Untuk data sensitif jangan gunakan Quick Tunnel tanpa autentikasi organisasi. `POC_LOOKUP_TOKEN` adalah lapisan keamanan sementara, bukan pengganti Entra ID/OAuth2 atau gateway enterprise. Jangan commit token, .env, atau connection string ke GitHub.

## 3. Hosting Excel Add-in

Upload **hanya** `web/taskpane.html` yang baru ke repo GitHub Pages (folder `web`), lalu commit ke branch `main`. File HTML berisi JS Office.js. `manifest.xml` lama POC03 yang sudah memberi `ReadWriteDocument` dapat digunakan ulang jika hostname dan lokasinya tetap sama.

`web/taskpane.html` URL tetap:

`https://meldanophia.github.io/mostrans-excel-poc/web/taskpane.html`

Jangan upload Flask, DATABASE_URL, atau file konfigurasi database ke GitHub Pages.

## 4. Uji dari Excel Online

1. Jalankan Flask port `6077`, lalu Cloudflare tunnel jika test dummy/staging diperbolehkan:

   `cloudflared tunnel --url http://localhost:6077`

2. Buka Excel POC dan add-in, isi URL sementara `.trycloudflare.com` yang baru.
3. **Baca A–K dan bentuk JSON**.
4. **Test Connection** untuk memastikan Flask versi 04.
5. **Lookup ID Master via Flask (SELECT)**: masukkan `POC_LOOKUP_TOKEN` yang sama dengan environment Flask. Tunggu ringkasan JSON `resolved_rows` dan `failed_rows`.
6. **Write-back ID Z:AD + Status AF:AH**: pada *salinan workbook POC*. Akan menolak penimpaan cell ID existing yang berbeda, menolak input yang telah berubah, dan mempertahankan AE.

Mapping output:

| Excel | Hasil |
|---|---|
| Z | transporter_id |
| AA | asal_kota_id |
| AB | tujuan_kota_id |
| AC | jenis_kendaraan_id |
| AD | tipe_harga_id |
| AE | **tidak disentuh** |
| AF | LOOKUP_OK / LOOKUP_FAILED |
| AG | pesan error lookup/validasi |
| AH | Row ID |

**Tidak ada query UPDATE mt_harga_transporter pada tahap ini.** POC05 baru membahas eksekusi dengan audit job, idempotency, safe transaction, dan error row; bukan bagian dari POC04.

## 5. Troubleshooting

- HTTP 401: `POC_LOOKUP_TOKEN` belum sama antara Flask dan panel.
- HTTP 503: `DATABASE_URL` hilang, `psycopg` belum diinstal, JSON mapping salah, koneksi gagal, nama tabel/kolom salah, atau `SELECT` belum diberikan. Baca log terminal Flask.
- `master tidak ditemukan`: nilai label Excel tidak persis sama dengan nama master; mapping exact/case-sensitive sengaja dipertahankan.
- `master ambigu`: beberapa ID punya nama persis sama, perlu aturan bisnis tambahan.
- Write-back gagal karena Z:AD sudah terisi: gunakan salinan Excel kosong untuk POC; jangan menghapus ID production tanpa backup.
- Valid date kosong `null` di JSON tidak menyebabkan lookup gagal.

## Catatan pengamanan data

Quick Tunnel bukan autentikasi jaringan. Walau endpoint lookup punya token sementara, hindari mengirim data harga/kredensial production melalui tunnel publik. Gunakan lingkungan staging, data dummy yang diizinkan, dan nantinya Entra ID, otorisasi user, TLS, rate limiting, serta reverse proxy internal.
