# Mostrans Price Tools — Excel Online Add-in POC

## Tujuan
POC **read-only** untuk memeriksa apakah tenant Microsoft 365 mengizinkan custom Office Add-in melalui **Upload My Add-in**, apakah ribbon button berfungsi, dan apakah Office.js dapat membaca kolom A–J di worksheet aktif. Tidak ada koneksi Flask, database, atau perubahan isi Excel.

## Isi paket
- `web/taskpane.html`: aplikasi web Office.js statis.
- `web/assets/icon16.png`, `icon32.png`, `icon80.png`: ikon ribbon.
- `manifest.template.xml`: manifest dengan placeholder `__BASE_URL__`.
- `build_manifest.py`: pembuat `manifest.xml` dari URL hosting HTTPS.
- `sample-data.csv`: contoh tiga data dummy (format CSV untuk paste/import di Excel).

## Cara termudah: hosting melalui GitHub Pages (khusus data dummy)
1. Buat repository GitHub **public** baru, misalnya `mostrans-excel-poc`. Jangan masukkan secret, data customer, atau file Excel produksi ke repository publik.
2. Upload seluruh isi folder `web/` ke folder `web/` pada repository.
3. GitHub repository → **Settings → Pages → Build and deployment → Deploy from a branch**, pilih `main` dan `/ (root)` → Save.
4. Setelah terbit, cek `https://USERNAME.github.io/mostrans-excel-poc/web/taskpane.html`. Mengakses di browser biasa mungkin menampilkan pesan agar dibuka dari Excel; itu normal.
5. Di folder proyek pada komputer, jalankan:
   ```bash
   python build_manifest.py https://USERNAME.github.io/mostrans-excel-poc/web
   ```
   Ini menghasilkan `manifest.xml` dengan URL HTTPS yang benar. Jika tak ingin Python, cari-ganti semua `__BASE_URL__` dalam `manifest.template.xml` dengan URL di atas lalu simpan sebagai `manifest.xml`.
6. Buka Excel Online dari SharePoint/OneDrive. Gunakan file **testing**, bukan production. Siapkan header di A1:J1 dan tiga data contoh pada baris 2–4.
7. **Home → Add-ins → More settings / Advanced → Upload My Add-in**, pilih `manifest.xml`, Upload.
8. Pada tab **Home** cari grup **Mostrans Tools**, klik **Read Excel Data**; panel akan terbuka.
9. Klik **Baca Kolom A–J**. Periksa hasil, preview dan jumlah baris, lalu coba **Copy JSON**.

## Alternatif hosting internal
Host seluruh isi `web/` pada origin HTTPS milik perusahaan (contoh `https://internal.example.co.id/poc/mostrans/web`) yang dapat diakses browser user. Lalu jalankan `build_manifest.py` dengan URL root tersebut. Tidak perlu GitHub publik.

## Kriteria sukses
- Manifest dapat di-upload tanpa error.
- Tombol `Read Excel Data` muncul di ribbon Home.
- Task pane dapat dibuka.
- Tiga row contoh terbaca tanpa mengubah data workbook.

## Troubleshooting
- **Manifest gagal di-upload**: validasi bahwa URL HTTPS sudah menggantikan seluruh `__BASE_URL__`, struktur XML benar, hosting dapat diakses, dan tenant mengizinkan sideloading.
- **Task pane kosong**: cek `taskpane.html` bisa dibuka lewat HTTPS dan Microsoft Office.js CDN tidak diblokir kebijakan jaringan.
- **Read Excel Data disabled**: halaman tidak dibuka dari konteks Excel atau Office.js belum siap.
- **Tidak muncul tombol**: cek Home ribbon dan daftar My Add-ins, lalu refresh workbook.
- **Data tidak terbaca**: contoh memerlukan header di baris 1 pada sheet aktif; maksimum 1000 baris data untuk POC.
- **GitHub Pages tidak diizinkan perusahaan**: pindahkan hosting ke layanan HTTPS internal.

## Catatan desain
- `ReadDocument` memberikan permission read-only untuk POC.
- No telemetry or API request besides loading Office.js CDN/hosted static assets; JSON remains on client until explicitly copied.
- Untuk POC production berikutnya, permission akan berubah jika perlu write-back, serta akan ada SSO dan backend Flask.
