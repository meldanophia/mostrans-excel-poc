# Mostrans Price Tools — Phase 2 (Staging UI)

## Tujuan
Mengganti banyak tombol POC 01–06 dengan dua aksi utama di Excel Online:
1. **Validate & Preview**: baca A–K, identitas row, validasi, master lookup, dan SELECT harga melalui Flask Phase 1.
2. **Confirm & Execute**: buat job idempotent, pantau worker, tulis error non-success di AF–AH, hapus row success setelah verifikasi.

**Status: UAT build, belum production release.** Tidak ada SQL di frontend. Menggunakan endpoint Flask Phase 1 yang sudah dibuat. Token staging dimasukkan pengguna (tidak di-commit dan tidak disimpan di browser). Untuk production gunakan Entra ID, hosting perusahaan dan host API internal terautentikasi.

## Artefak
- `web/taskpane.html`: halaman Office Add-in satu file.
- `taskpane.js`: salinan JavaScript untuk syntax check; *tidak perlu di-upload*.
- Tidak mengubah `app.py`, `worker.py`, `.env`, maupun DDL yang sudah digunakan di Phase 1.

## Deploy bertahap
1. **Backup** `web/taskpane.html` POC 06 dan salinan workbook. Jangan uji penghapusan baris pada workbook produksi.
2. Ganti hanya `web/taskpane.html` di branch testing/deployment GitHub Pages, lalu buka URL HTTPS dan pastikan judul **Phase 2 (Staging)** muncul.
3. Pastikan manifest yang di-upload memiliki `<Permissions>ReadWriteDocument</Permissions>` dan resource task pane mengarah ke URL yang benar. Bila Office Online tetap menampilkan POC lama, gunakan `?v=phase2-1` pada kedua `SourceLocation` di manifest dan instal ulang bila diperlukan. **Jangan mengubah URL icon menjadi `taskpane.html/assets`.**
4. Gunakan workbook salinan dengan header A–K persis: `no SK`, `Transporter`, `Asal Kota`, `Tujuan Kota`, `Jenis Kendaraan`, `Tipe Muatan`, `Tipe Harga`, `Start Date`, `Price`, `TKBM`, `Valid Date`.
5. **ALLOWED_ORIGIN di Flask** adalah origin hosting add-in tanpa path, misalnya `https://meldanophia.github.io`, bukan full `https://.../mostrans-excel-poc/web/taskpane.html`. Restart Flask setelah perubahan `.env`.
6. Isi **Flask HTTPS URL** (base origin, tanpa path) dan **STAGING_API_TOKEN** secara manual. Token tidak boleh dimasukkan ke repo/manifes ataupun screenshot.
7. Klik **Validate & Preview**: hasil READY/Issue harus cocok dengan `POST /api/v1/transporter-prices/preview` pada PowerShell.
8. Untuk memeriksa UI sekarang, biarkan `ENABLE_PRICE_UPDATE=false` dan gunakan tombol Preview saja. Tombol Execute akan gagal dengan pengaman backend; ini benar dan tidak perlu diakali.
9. Uji **Confirm & Execute** hanya setelah endpoint API HTTPS internal dengan autentikasi, DDL job, backend worker, dan akun database staging diperiksa. Backend Phase 1 dengan sengaja menolak Quick Tunnel dan request non-HTTPS.

## Perilaku Excel & recovery
- Sheet input: user pilih sheet harga, misalnya `Sheet1`/`Lembar1`.
- Input A–K; `valid_date` pada K adalah VARCHAR nullable berformat `[YYYY-MM-DD,YYYY-MM-DD]`. Nilai kosong dikirim `null`.
- Kolom AH berisi **row_id stabil** (UUID); ID POC lama `Sheet1:row-2` akan diganti saat Preview.
- Worksheet tersembunyi `_MOSTRANS_META` menyimpan workbook_id, job_id, request_key, stage, dan **snapshot input original**. Tidak menyimpan token.
- Saat job `completed`, add-in mengambil `/results` lalu membandingkan input dengan snapshot dan digest backend. Row `success` dihapus dari bawah ke atas. Row `failed`, `skipped`, dan `stale` dipertahankan beserta error AF–AH.
- `sync-ack` baru dikirim jika cleanup dan verifikasi berhasil. Menekan **Resume Job & Excel Sync** tidak membuat job UPDATE baru.
- Pengguna harus menghentikan editing data selama Preview → Execute → Sync. Konflik snapshot menyebabkan cleanup ditolak.
- Worksheet input tidak boleh memiliki formula/tabel lain yang perlu dipertahankan di luar area data pada baris yang dihapus; penghapusan dilakukan terhadap baris penuh.

## API yang dipanggil
- `POST /api/v1/transporter-prices/preview`
- `GET /health`
- `POST /api/v1/transporter-prices/jobs` dengan `Idempotency-Key`
- `GET /api/v1/transporter-prices/jobs/by-request-key`
- `GET /api/v1/transporter-prices/jobs/{job_id}`
- `GET /api/v1/transporter-prices/jobs/{job_id}/results`
- `POST /api/v1/transporter-prices/jobs/{job_id}/sync-ack`

## Kriteria UAT sebelum production
- Preview 1 READY + 1 NOT_FOUND + 1 INVALID, nilai ID lookup cocok dengan DB.
- Replay Preview saat data diubah menghasilkan preview baru; Execute menggunakan proof yang kedaluwarsa ditolak.
- POST job dengan idempotency key yang sama tidak membuat job ganda.
- Browser ditutup sebelum respons POST, recovery dengan key tersimpan bisa menemukan job yang sama.
- Browser ditutup saat partial cleanup: resume tidak mengeksekusi SQL ulang dan tidak menghapus row yang berubah.
- Jika semua row sukses terhapus, sheet masih menyisakan header dan `sync-ack` berhasil.
- Worker crash saat status running memerlukan prosedur operator (worker Phase 1 tidak otomatis me-replay transaksi tidak pasti).
- UAT 100–1000 row untuk latensi dan batas layanan Excel Online.

## Known limitations / blockers menuju production
1. **Security**: `STAGING_API_TOKEN` dalam task pane adalah hanya untuk staging. Ganti dengan Microsoft Entra ID delegated access token / NAA + validasi JWT di Flask, dan deployment internal yang tidak membuka Execute via Quick Tunnel.
2. **Input permissions**: Office Add-in harus menggunakan `ReadWriteDocument` (pengalaman POC menunjukkan `ReadDocument` menyebabkan write-back gagal).
3. **Workbook edits**: add-in tidak mengunci sheet selama operasi; pengguna/tim harus menghindari perubahan bersamaan. Untuk produksi, tambahkan koordinasi lock workbook/job dan mekanisme konflik yang teruji.
4. **Preview proof TTL**: backend Phase 1 hanya menerima preview proof hingga 10 menit. Ulangi Preview jika kedaluwarsa.
5. **Job UAT**: Phase 1 job worker pernah disiapkan, tetapi belum dilaporkan teruji end-to-end oleh user. Jangan menganggap Execute Phase 2 sudah PASSED.
6. **Recovery integrity**: snapshot ada dalam worksheet tersembunyi, bukan storage anti-tamper. Backend tetap harus memastikan otorisasi pemilik workbook/job dan identitas pengguna untuk produksi. Jangan menyimpan data sensitif di file publik.
7. **Retention**: jangan hapus job `pending sync` setelah tujuh hari; simpan sampai recovery selesai.

## Testing statis
`node --check taskpane.js`
