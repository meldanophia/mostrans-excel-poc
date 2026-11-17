# POC 05.3 — Restore contiguous writes

Mengembalikan pola write-back POC 03.2 yang sudah berhasil: satu blok `AF1:AHn` untuk validasi, dua blok `Z1:ADn` dan `AF1:AHn` untuk lookup. Tidak memakai N request per-row.

## Update
1. Commit hanya `web/taskpane.html` ke GitHub Pages.
2. Restart Excel Online / hard refresh dan lihat label `POC 05.3`.
3. Gunakan workbook salinan. Baca A–K → validasi Flask → write-back AF–AH.
4. Lanjutkan lookup → write-back Z–AD & AF–AH.
5. Jika masih berhenti, periksa DevTools Console pada konteks iframe `taskpane.html`, cari error `[Mostrans]`.

Tidak perlu update Flask, `.env`, maupun manifest jika URL taskpane sudah benar. Jangan mengaktifkan Execute Staging melalui tunnel publik.
