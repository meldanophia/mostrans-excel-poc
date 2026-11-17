# Mostrans Excel Add-in — POC 03.1 (Valid Date nullable VARCHAR)

## Perubahan dari POC 03
- Excel **kolom K (Valid Date)** boleh kosong; Office Add-in mengirim **JSON null**, bukan string kosong.
- Jika terisi, format literal yang diterima **`[YYYY-MM-DD,YYYY-MM-DD]`** tanpa spasi. Contoh `[2026-11-17,2026-11-17]`.
- Flask memvalidasi format, tanggal kalender dan urutan tanggal; **tidak mengonversi ke daterange**. Return setiap row mencantumkan `valid_date` berupa string persis atau null.
- SQL referensi mencocokkan kolom VARCHAR secara null-safe dengan **`h.valid_date IS NOT DISTINCT FROM %(valid_date)s::varchar`**. `NULL` hanya cocok dengan `NULL`.
- Write-back hasil **validasi saja** ke AF:AH tetap seperti POC sebelumnya. `valid_date` kosong bukan penyebab gagal validasi. Belum ada SQL yang dieksekusi atau penghapusan row sukses.

## Contoh payload Office Add-in
```json
{"operation":"POC_VALIDATE_INACTIVE_PRICE_NO_SQL","rows":[
 {"row_id":"Sheet1:row-2","sheet_row":2,"valid_date":"[2026-11-17,2026-11-17]"},
 {"row_id":"Sheet1:row-3","sheet_row":3,"valid_date":null}
]}
```
> Ini ilustrasi field terkait; request sesungguhnya menyertakan kolom A–J lengkap.

## Cara deploy
1. Extract ZIP. Replace **`web/taskpane.html`** di GitHub repo `mostrans-excel-poc`, commit ke `main`, lalu refresh Excel Online / task pane setelah Pages deploy.
2. **Tidak perlu re-upload manifest** jika sebelumnya POC 03 sudah memakai `ReadWriteDocument` dan URL halaman sama. File manifest di ZIP hanya untuk instalasi baru.
3. Stop Flask POC 03 yang lama (`Ctrl+C`) dan jalankan versi baru:
   ```powershell
   pip install flask
   python flask_poc_api.py
   ```
4. Jalankan tunnel HTTPS (jika tunnel sebelumnya masih hidup, bisa dipakai):
   ```powershell
   cloudflared tunnel --url http://localhost:6077
   ```
5. Di workbook **salinan dengan data dummy**, klik **Baca A–K** → **Validasi A–K** → jika diinginkan **Tulis status ke Excel (AF:AH)**.

## Hasil yang diharapkan
- Baris dengan K kosong: `valid_date: null`, bisa `valid` jika seluruh kolom wajib lain valid.
- Baris dengan K `[2026-11-17,2026-11-17]`: bisa `valid`.
- Baris dengan K `[2026-11-17 – 2026-11-17]` atau `[2026-11-17, 2026-11-17]`: `invalid` (format salah).
- Baris dengan K `[2026-12-31,2026-01-01]`: `invalid` (urutan salah).

## Keamanan & scope
Flask `/poc/validate` adalah **validasi saja**; tidak ada DB connection atau UPDATE. Endpoint Quick Tunnel dapat diakses publik oleh pihak yang mengetahui URL, jadi gunakan data dummy saja. Untuk production, siapkan Entra ID authentication, authorization, durable jobs, backend ID lookup, transactions, retry protection dan write-back aman. Query `sql_inactive_template.py` hanya referensi dan belum dipakai API.


## POC 03.2 — Troubleshooting write-back
- Memperbaiki perilaku tombol yang sebelumnya mengandalkan `window.confirm()` di dalam task pane Office Add-in. Konfirmasi bawaan browser bisa diblokir/diabaikan oleh host iframe sehingga tombol tidak menjalankan penulisan. Sekarang tombol langsung memulai proses (hanya pada workbook **dummy**).
- Progress `Memulai write-back` / `Menulis ...` dan detail exception muncul langsung di bawah tombol.
- **Tetap validasi saja**, tanpa SQL atau perubahan A–AE; target hanya AF–AH.
- Setelah commit penggantian `web/taskpane.html`, buka `https://meldanophia.github.io/mostrans-excel-poc/web/taskpane.html` dan pastikan header menunjukkan **POC 03.2**. Refresh task pane Excel, lalu ulangi Baca A–K → Validasi A–K → Tulis status validasi.
- Jika muncul error `Kolom AF:AH sudah dipakai`, jangan kosongkan otomatis; periksa apakah kolom tersebut memiliki data penting.
