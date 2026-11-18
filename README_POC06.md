# Mostrans POC 06 — Final Write-back / Cleanup

## Tujuan
Membaca **hasil Execute yang sudah committed** dari `public.mt_poc_price_execution_log`, lalu dari Excel Online menulis status/error ke AF–AH dan **menghapus seluruh row berstatus `success` saja**. `failed`, `skipped`, dan `stale` tetap terlihat. POC06 tidak menjalankan SQL UPDATE sama sekali.

## Instalasi
1. Ganti `web/taskpane.html` di GitHub Pages (main). Manifest mesti memiliki `<Permissions>ReadWriteDocument</Permissions>`. Jika cache, ubah URL manifest taskpane menjadi `?v=6` dan pasang ulang add-in.
2. Ganti `poc05_extension.py` di Flask POC kamu. File versi ini memakai nama tabel log yang sudah kamu rename: `public.mt_poc_price_execution_log`. File `flask_poc_api.py` dari POC05 tetap dapat digunakan (mengimpor extension ini). Jangan mengganti `.env` atau `master_lookup.json` yang telah disiapkan.
3. `python flask_poc_api.py`, gunakan endpoint HTTPS staging yang diizinkan. Untuk POC 06 sendiri endpoint `/poc/price-results` hanya `SELECT`. Hindari data bisnis sensitif melalui tunnel publik.
4. Pakai **SALINAN workbook** yang sama persis dengan input eksekusi POC05 (termasuk nomor/posisi row sebelum cleanup). Jalankan **Baca A–K**; isi API URL + token; masukkan **job_key dari log POC05** (lihat query di bawah). Tekan **Ambil Hasil Eksekusi**.
5. Bila seluruh `input_digest` identik dan status terminal, centang persetujuan lalu klik **Final Write-back & Hapus Row Success**. POC akan menulis AF–AH terlebih dahulu, kemudian menghapus baris sukses dari bawah ke atas.
6. Jika terputus: **jangan ulang UPDATE**. Buka kembali workbook, **Baca A–K** dan ambil job_key yang sama. AH menyimpan ID asal untuk row yang masih ada; POC akan menghapus hanya success yang tersisa.

```sql
SELECT job_key, row_id, status, target_id, error_message, input_digest
FROM public.mt_poc_price_execution_log
ORDER BY id DESC LIMIT 50;
```

## Ekspektasi untuk contoh log kamu
4 baris: `success` (row 2,3,4), `skipped` (row 5). Setelah cleanup, row asli 2–4 dihapus, row yang `skipped` bergeser ke row 2 dan error `Dry-run tidak READY` tetap tertera pada AG. AH menyimpan `Lembar1:row-5` sehingga retriable.

## Pengaman dan batasan
- POC06 memeriksa digest input dari log server sebelum menyentuh worksheet. `row_id` berformat sheet + baris asal; AH dipakai menjaga identitas saat baris bergeser. Perhitungan digest menggunakan `sheet_row` original dari `row_id`, bukan posisi Excel terkini. Tidak menerima status sukses dari JSON buatan client.
- Seluruh baris Excel dihapus dengan `getEntireRow().delete` (bukan hanya rentang A–AH). **Jangan gunakan di workbook production atau worksheet yang memiliki informasi lain di luar tabel.**
- Setiap row success dihapus dengan `context.sync()` terpisah; operasi tidak atomik. Recovery dibatasi pada workbook yang belum diubah user dan job yang sama.
- POC06 tidak menghapus histori di PostgreSQL dan tidak memerlukan tabel baru. Pertahankan `mt_poc_price_execution_log` selama fase POC.
- POC05 tetap menggunakan tabel POC untuk log transaksi selama pengujian. Pada migrasi final sesudah POC06, kamu meminta **tidak menggunakan** tabel POC dan **sebisa mungkin memodifikasi `app.py` existing**. Itu pekerjaan terpisah yang belum diaplikasikan di paket ini.
- File `app.py` existing masih memakai `gspread`, service account Google, query dari sheet dan pola delete-all/append-failed; untuk produksi harus direfaktor menjadi API Excel JSON + backend parameterized SQL + status hasil, bukan menggunakan jalur Google Sheets tersebut.
- Tidak ada penerapan auth perusahaan/worker queue pada paket ini. Jangan jadikan paket POC sebagai deployment production.
