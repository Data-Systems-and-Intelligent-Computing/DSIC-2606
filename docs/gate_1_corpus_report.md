# Laporan Korpus Eksperimen — Fase 1

**Status:** Seleksi korpus eksperimen Main, manifest 300 rekaman, dan urutan 30 batch telah dibuat di laptop. Test suite yang dijalankan setelah perubahan melaporkan 9 test lulus. Pencocokan independen dengan salinan korpus di VM/bucket, pembekuan corpus.sha256, dan metadata acuan masih menunggu langkah berikutnya.

## Ruang Lingkup

Eksperimen utama bulan pertama menggunakan korpus Main (MAIN_5JAM). Korpus Kantin, Embung D, dan Kebun Raya disimpan sebagai korpus robustness dan tidak dimasukkan ke matriks utama Fase 1.

## Korpus Main

Aturan seleksi yang ditetapkan sebelum membentuk manifest: file WAV yang ukurannya berbeda dari ukuran modal dikeluarkan dari subset eksperimen. File mentah tetap disimpan. Pengecualian ini merupakan aturan seleksi ukuran; hal ini tidak dengan sendirinya membuktikan penyebab atau kondisi rekaman.

| Metrik | Hasil subset eksperimen Main |
|---|---:|
| WAV sumber sebelum seleksi | 301 |
| WAV di manifest eksperimen | 300 |
| File dikecualikan | 20260924_183232.WAV (488 byte) |
| Ukuran modal dan ukuran setiap file terpilih | 3.520.800 byte |
| Total byte subset terpilih | 1.056.240.000 byte (1.007,31 MiB) |
| Rentang timestamp mulai (UTC) | 2026-09-24 06:30:00 – 11:29:00 |
| Label device_id di manifest | MAIN_5JAM |
| Urutan batch beku | 30 batch × 10 rekaman |
| Micro-batch Spark aktual | Belum diverifikasi; tidak disimpulkan dari batch order |

source_path di manifest menggunakan jalur relatif terhadap akar repo. Nilai sha256 dibuat dari file WAV sumber oleh generator manifest.

## Korpus Robustness — Catatan EDA Sebelumnya

Angka berikut dipertahankan sebagai catatan profiling sebelumnya; korpus ini tidak masuk ke matriks utama bulan pertama.

| Lokasi/sesi | Jumlah WAV | Distribusi ukuran yang tercatat | Rentang timestamp (UTC) |
|---|---:|---|---|
| Kantin | 121 | 120 × 3.520.800 byte; 1 × 488 byte | 2026-09-23 03:00:00 – 05:01:45 |
| Embung D | 101 | 100 × 3.520.800 byte; 1 × 488 byte | 2026-09-25 05:10:00 – 06:58:30 |
| Kebun Raya | 100 | 100 × 3.520.800 byte | 2026-09-24 04:10:00 – 05:49:00 |
| Total robustness | 322 | 320 × 3.520.800 byte; 2 × 488 byte | Tiga rentang lokasi di atas |

## Test dan Bukti yang Tersedia

Perintah yang dijalankan setelah manifest dan urutan batch dibentuk ulang:

    python -m unittest discover -s tests -v
    Ran 9 tests in 0.102s
    OK

Hasil ini membuktikan 9 test yang ditemukan oleh unittest discover lulus pada saat dijalankan. Hasil ini belum membuktikan kecocokan file WAV di VM dengan manifest.

## Sisa Pekerjaan Fase 1

- Verifikasi nama, ukuran, dan SHA-256 terhadap salinan korpus di VM menggunakan verify_corpus.py.
- Uji negatif verifier pada salinan uji, bukan pada korpus sumber.
- Buat dan simpan corpus.sha256, lalu bekukan direktori korpus eksperimen.
- Tetapkan skema metadata dan buat expected_metadata.csv yang memuat nilai acuan untuk rekonsiliasi.
- Lengkapi provenance perangkat fisik dan firmware dari CONFIG.TXT.
- Jalankan uji yang secara khusus membuktikan nama file dengan timestamp tidak valid menggagalkan generator.
