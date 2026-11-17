# POC 05.4 — Isolasi Office.js write-back

1. Upload `web/taskpane.html` ke repository GitHub Pages, menggantikan versi POC 05.3.
2. Pastikan halaman langsung menampilkan POC 05.4, tutup/reopen add-in di Excel Online; gunakan cache-busting manifest bila perlu.
3. **Gunakan salinan workbook testing**. Refresh workbook sebelum melakukan tes diagnostik.
4. Klik **Test tulis 1 sel (AI2)**. Ini menulis TEST_OK ke AI2, tidak menyentuh A–K, Z–AD, AF–AH, atau DB.
5. Jika AI2 sukses, baru jalankan validasi dan write-back AF–AH. Jika AI2 gagal/hanging, jangan teruskan SQL Update.
6. Buka DevTools Console, pilih frame GitHub Pages taskpane bila tersedia. Cari `[Mostrans POC05.4]`.

Catatan: Watchdog 15 detik hanya menampilkan status stuck, bukan membatalkan operasi Office.js. Jangan langsung melakukan retry jika workbook masih memproses perubahan.
