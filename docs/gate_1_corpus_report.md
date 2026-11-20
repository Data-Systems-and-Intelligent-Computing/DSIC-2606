# Laporan Korpus Eksperimen — Fase 1

**Status korpus: Beku. Status Gate Minggu 1: ditutup bersyarat (D-41).** Laporan ini merangkum pemilihan subset Main, manifest dan urutan batch, pencocokan terhadap salinan di Lightsail, uji negatif verifier, checksum korpus, metadata acuan, serta bukti B0/B1 F0. Syarat dokumentasi D-41 dicatat di bawah; pembimbing telah mengizinkan dimulainya Minggu 2.

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

### Perhitungan ringkasan dari skrip

Pada 30 Oktober 2026, pengguna menjalankan `python scripts/corpus_report.py` dari PowerShell di akar repo. Skrip membaca manifest Main, batch order, empat salinan `CONFIG.TXT`, dan folder sumber raw lokal bila tersedia. Keluaran yang dilaporkan:

```text
Korpus eksperimen Main (dari manifest):
  jumlah berkas       : 300
  total byte          : 1,056,240,000
  perangkat fisik     : 1 (Device ID unik dari CONFIG.TXT)
  rentang waktu UTC   : 2026-09-24T06:30:00Z s.d. 2026-09-24T11:29:00Z
  jumlah batch beku   : 30
  distribusi ukuran   : 3,520,800 byte: 300 file
  ukuran tiap batch   : 30 batch x 10 recording_id
Korpus sumber mentah (dari folder raw, termasuk file yang dikecualikan):
  jumlah berkas       : 301
  total byte          : 1,056,240,488
  rentang waktu UTC   : 2026-09-24T06:30:00Z s.d. 2026-09-24T11:32:32Z
  distribusi ukuran   : 488 byte: 1 file; 3,520,800 byte: 300 file
```

Hasil skrip sesuai dengan angka subset dan sumber mentah pada tabel di atas. Jumlah perangkat fisik berasal dari Device ID unik pada `CONFIG.TXT`, bukan dari label sesi `device_id` di manifest.

File `20260924_183232.WAV` (488 byte) dikecualikan dari subset karena ukurannya berbeda dari ukuran modal. File mentahnya tetap disimpan; pada VM file ini dipisahkan dari `/data/corpus/main` ke `/data/corpus/dikeluarkan/`. Karena itu angka sumber mentah (301 file) dan subset eksperimen (300 file) memang berbeda.

Pada manifest eksperimen, `recording_id` berjumlah 300 dan semuanya unik. `source_path` dicatat relatif terhadap akar repo. Nilai SHA-256 pada manifest dibentuk dari file WAV sumber.

## Provenans Perangkat dan Zona Waktu

Empat `CONFIG.TXT` sesi Main, Kantin, Embung D, dan Kebun Raya mencatat Device ID fisik yang sama. Berdasarkan empat konfigurasi tersebut, jumlah perangkat fisik yang teridentifikasi adalah **1**. `device_id` di manifest tetap merupakan label sesi (`MAIN_5JAM`), sedangkan Device ID fisik dicatat terpisah di [`device_provenance.md`](device_provenance.md).

Konfirmasi pembimbing pada 23 September 2026 menyatakan waktu perangkat saat perekaman menggunakan waktu lokal UTC+7. Timestamp nama file Main dikonversi dari `Asia/Jakarta` ke UTC; contoh file pertama `20260924_133000.WAV` menjadi `2026-09-24T06:30:00Z`.

## Urutan Batch dan Micro-batch

`data/batches/batch_order_main.csv` berisi 300 penempatan rekaman dalam **30 batch**, masing-masing tepat 10 rekaman. Keluaran pemeriksa pada log B0/F0 dan B1/F0 masing-masing menyatakan `30 batch x 10 ID COCOK dengan batch_order_main.csv`; bukti tersimpan di `docs/evidence/verify-batches-b0-f0-20261120.txt` dan `docs/evidence/verify-batches-b1-f0-20261120.txt`.

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

Pada 20 November 2026, setelah penambahan uji bahasa klaim dan uji negatif integritas manifest, `python -m unittest discover tests -v` melaporkan `Ran 30 tests in 1.078s` dan `OK` (30 lulus, 0 gagal; kode keluar 0). Keluaran aktual disimpan di `docs/evidence/unittest-gate-week1-20261120.txt`. Uji bahasa klaim juga diuji dengan frasa terlarang sementara: test gagal dengan kode 1 saat frasa ada dan lulus lagi setelah probe dihapus; keluaran tersimpan di `docs/evidence/claim-language-20261120.txt`.

## Status butir Gate Minggu 1

| # | Kriteria | Status berdasarkan bukti repo saat ini |
|---:|---|---|
| 1 | RQ, sub-RQ, batas publikasi, dan logbook | **Syarat D-41 dikerjakan:** RQ dan batas publikasi berstatus berlaku dengan rujukan D-03; bagian RQ di `paper/manuscript.md` diselaraskan dengan RQ1–RQ5. |
| 2 | Korpus beku, cocok di Lightsail, SHA-256 lengkap | **Lulus di Lightsail:** pemeriksaan ulang 20 November menunjukkan 300/300 cocok, 0 berkas hilang/berlebih/tidak cocok, dan SHA-256 exit 0. Keluaran mentah telah disalin ke `docs/evidence/week1-day2-corpus-20261120.log`. |
| 3 | Urutan masukan dan komposisi batch beku | **Lulus:** 30 batch × 10 ID cocok pada B0/F0 dan B1/F0. |
| 4 | Angka korpus dilaporkan | **Lulus:** statistik dihitung skrip dan dicatat pada laporan ini. |
| 5 | Minimal 10 micro-batch | **Lulus:** 30 micro-batch pada B0/F0 dan B1/F0. |
| 6 | Aturan `recording_id` dan `expected_object_uri` dibekukan | **Lulus:** aturan dicatat pada `docs/correctness-invariants.md` dan diuji terhadap manifest. |
| 7 | Uji stabilitas identitas termasuk kasus negatif | **Lulus:** test identitas konsisten; timestamp tanpa zona waktu ditolak. |
| 8 | Tidak ada ID duplikat atau SHA-256 kosong/invalid, termasuk uji negatif | **Lulus lokal:** test integritas manifest memeriksa empat manifest dan menolak ID duplikat, ID kosong, hash kosong, serta hash invalid. |
| 9 | Versi dan batas sumber daya dibekukan | **Lulus di Lightsail:** `make check` cocok dengan `environment.lock.txt`; self-test 31/31 mencakup pemeriksaan lock, reset, preflight, dan batas sumber daya. Keluaran Hari 5 tersimpan di `docs/evidence/week1-day5-*.log`. |
| 10 | Ambang multipart diverifikasi dengan WAV eksperimen | **Lulus:** B0/F0 dan B1/F0 masing-masing memeriksa 300 objek dan melaporkan 0 multipart; klien dan ambang dicatat di `configs/environment.yaml`. |
| 11 | B0/B1 berjalan F0, beda satu kunci, perilaku checkpoint terbukti | **Lulus:** kedua F0 300 objek/300 baris; log efektif beda hanya `checkpoint_location`; bukti restart B0 dan B1 ada. |
| 12 | B0 baseline wajar, bukan sengaja dilemahkan | **Lulus:** paragraf ada di `docs/treatment-semantics.md`, commit `b98358f` mendahului eksekusi F0. |

## Catatan penutupan bersyarat D-41

- Keputusan D-03 menetapkan rumusan RQ di README sebagai acuan. Status dan penyelarasan dokumen diperbarui mengikuti D-41.
- Keluaran mentah Hari 1, Hari 2, dan Hari 5 sudah disalin ke `docs/evidence/`; rincian snapshot, sinkronisasi repo, verifikasi korpus, dan self-test dicatat di logbook.
- Perubahan dokumen D-41 perlu masuk ke commit berikutnya bersama logbook dan laporan yang diperbarui.

Gate Minggu 1 ditutup **bersyarat**, bukan sebagai klaim bahwa hipotesis penelitian telah diuji. Eksperimen F1–F3 dan hipotesis masih menjadi pekerjaan fase berikutnya.
