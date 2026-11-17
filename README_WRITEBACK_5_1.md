# POC 05.1 — write-back diagnostics

Perubahan hanya pada `web/taskpane.html` (tanpa perubahan Flask/database).

- Write-back validasi AF:AH dan ID Z:AD + AF:AH menggunakan chunk 5 row.
- Setiap chunk diverifikasi dengan pembacaan ulang Office.js.
- Tidak menimpa ID berbeda atau AF:AH milik proses lain.
- Aman mengulangi bila sebagian chunk selesai; tulis ulang nilai yang sama.
- Mode dry run dan SQL execute tidak diubah oleh patch ini.
- Pastikan workbook adalah salinan POC, lalu refresh Office Add-in; bila cache memakai versi lama, gunakan cache-busting manifest `?v=5.1`.
- Jika berhenti, screenshot pesan status batch dan console error (sensor informasi rahasia).
- Pertama uji Baca A-K -> Validasi -> Write-back; kemudian Lookup -> Write-back.

Perhatikan: Excel Online bisa tertahan di `ctx.sync()` karena host/network; chunk + status tahap memperkecil cakupan diagnosa, namun tidak menjamin menyelesaikan masalah sisi layanan.
