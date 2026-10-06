# Laporan Korpus Eksperimen — Fase 1

**Status: Sedang ditinjau.** Laporan ini merangkum pemilihan subset Main, manifest dan urutan batch, pencocokan terhadap salinan di VM, uji negatif verifier, checksum korpus, serta metadata acuan. Status tetap ditinjau sampai seluruh artefak Fase 1 diperiksa dan commit final dicatat.

## Ruang Lingkup

Eksperimen utama bulan pertama menggunakan subset korpus Main (`MAIN_5JAM`). Kantin, Embung D, dan Kebun Raya merupakan korpus robustness dan tidak dimasukkan ke matriks utama Fase 1.

## Korpus Main

**Aturan seleksi yang digunakan:** WAV yang ukurannya berbeda dari ukuran modal dikeluarkan dari subset eksperimen Main; file mentah tetap dipertahankan. Aturan ini menyeleksi berdasarkan ukuran file dan tidak menyimpulkan penyebab atau kondisi rekaman.

| Metrik | Korpus sumber mentah | Subset eksperimen Main |
|---|---:|---:|
| Jumlah WAV | 301 | 300 |
| Total ukuran | 1.056.240.488 byte | 1.056.240.000 byte |
| Distribusi ukuran | 300 × 3.520.800 byte; 1 × 488 byte | 300 × 3.520.800 byte |
| Rentang timestamp mulai (UTC) | 2026-09-24 06:30–11:32:32 (termasuk file 488 byte) | 2026-09-24 06:30–11:29 |
| Jumlah batch | — | 30 batch × 10 rekaman |

File `20260924_183232.WAV` (488 byte) dikecualikan dari subset karena ukurannya berbeda dari ukuran modal. File mentahnya tetap disimpan; pada VM file ini dipisahkan dari `/data/corpus/main` ke `/data/corpus/dikeluarkan/`. Karena itu angka sumber mentah (301 file) dan subset eksperimen (300 file) memang berbeda.

Pada manifest eksperimen, `recording_id` berjumlah 300 dan semuanya unik. `source_path` dicatat relatif terhadap akar repo. Nilai SHA-256 pada manifest dibentuk dari file WAV sumber.

## Provenans Perangkat dan Zona Waktu

Empat `CONFIG.TXT` sesi Main, Kantin, Embung D, dan Kebun Raya mencatat Device ID fisik yang sama. Berdasarkan empat konfigurasi tersebut, jumlah perangkat fisik yang teridentifikasi adalah **1**. `device_id` di manifest tetap merupakan label sesi (`MAIN_5JAM`), sedangkan Device ID fisik dicatat terpisah di [`device_provenance.md`](device_provenance.md).

Konfirmasi pembimbing pada 23 September 2026 menyatakan waktu perangkat saat perekaman menggunakan waktu lokal UTC+7. Timestamp nama file Main dikonversi dari `Asia/Jakarta` ke UTC; contoh file pertama `20260924_133000.WAV` menjadi `2026-09-24T06:30:00Z`.

## Urutan Batch dan Micro-batch

`data/batches/batch_order_main.csv` berisi 300 penempatan rekaman dalam **30 batch**, masing-masing tepat 10 rekaman. Ini adalah urutan batch yang dibekukan untuk eksperimen. Jumlah tersebut **bukan** bukti jumlah micro-batch Spark aktual; konfigurasi dan keluaran micro-batch Spark belum diverifikasi.

## Verifikasi Korpus di VM

Pencocokan manifest dengan `/data/corpus/main` menggunakan `verify_corpus.py` menghasilkan:

```text
baris manifes : 300
berkas di disk: 300
hilang        : 0 []
berlebih      : 0 []
tidak cocok   : 0 []
HASIL: COCOK
kode keluar: 0
```

Uji negatif dilakukan pada direktori salinan `/data/work/uji-negatif`, bukan pada korpus beku. Salinan berisi dua file dan salah satunya diubah dengan menambahkan satu byte. Hasilnya:

```text
baris manifes : 300
berkas di disk: 2
hilang        : 298
berlebih      : 0 []
tidak cocok   : 1 ['20260924_133000.WAV']
HASIL: TIDAK COCOK
kode keluar: 1
```

Hasil uji negatif ini sesuai harapan: verifier mendeteksi satu file yang berubah dan file acuan lain yang tidak ada pada salinan uji. Direktori uji kemudian dihapus.

Direktori `/data/corpus/main` di VM dibuat tidak dapat ditulis. Berkas `data/manifests/corpus.sha256` dibuat dari 300 WAV pada korpus beku VM. Jumlahnya **300 baris**; salinannya telah ditempatkan di repo lokal dengan ukuran **25.800 byte**.

## Metadata Acuan

Skema metadata ditetapkan pada `schemas/metadata_record.schema.json`. Skrip pembentuk ground truth membaca manifest Main dan menghasilkan `data/ground_truth/expected_metadata.csv` dengan **300 baris** dan kolom `recording_id`, `device_id`, `start_time`, `object_uri`, `file_size_bytes`, dan `sha256`. Berkas ini dibentuk dari manifest sebelum pipeline ingesti dijalankan dan menjadi nilai acuan rekonsiliasi.

Aturan perbandingan kolom dan pemetaan invarian I1–I7 dicatat di [`correctness-invariants.md`](correctness-invariants.md). Metadata runtime seperti `ingestion_time` dan `run_id` tidak dimasukkan ke ground truth.

## Hasil Test

Pada 7 Oktober 2026, perintah `python -m unittest discover -s tests -v` melaporkan `Ran 9 tests in 0.180s` dan `OK` (9 lulus, 0 gagal). Ini adalah keluaran yang dilaporkan pengguna. Perubahan sesudahnya hanya memperbarui catatan waktu VM di dokumentasi; tidak ada perubahan kode atau konfigurasi setelah test tersebut.

## Sisa Pekerjaan Sebelum Gate 1 Ditutup

- Jalankan dan catat uji khusus yang membuktikan generator manifest berhenti dengan galat ketika nama file tidak dapat diurai sebagai timestamp.
- Pastikan `corpus.sha256`, empat salinan `CONFIG.TXT`, skema, expected metadata, manifest, batch order, laporan, dan logbook masuk ke commit yang sama.
- Hasil pembuatan expected metadata, provenance perangkat, dan konfirmasi status VM `TERMINATED` pada 2026-10-07 01:25:22 +07:00 telah dicatat di logbook.
- Catat hash commit final saat mengirim bukti Fase 1 kepada pembimbing.
- Pertahankan status laporan **Sedang ditinjau** sampai pemeriksaan akhir Fase 1 selesai.
