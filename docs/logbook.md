# Logbook Penelitian 
**Proyek:** DSIC-2606 Checkpointing & Idempotence AudioMoth Ingestion

---

### Entri: 23 September 2026
* **Lokasi & Kegiatan:** Kantin – *Deployment* AudioMoth (Durasi rekaman: 2 jam, 10:00 - 12:00 WIB).
* **Hasil:** Diperoleh 121 items (120 file `.WAV` sebagai *payload* utama, ukuran total ~403 MB, dan 1 file `CONFIG.TXT`).
* **Kendala:** Perangkat fisik sempat disentuh pihak eksternal, sehingga alat harus dipindahkan ke meja sendiri demi keamanan data.
* **Keputusan:** Pengambilan data dihentikan sesuai jadwal, data diamankan langsung ke *local storage*.

---

### Entri: 24 September 2026
* **Lokasi & Kegiatan:** Kebun Raya – *Deployment* AudioMoth dengan **dua skema** perekaman:
  1. **Skema 1:** Durasi 1 jam 40 menit (menghasilkan 101 items: 100 file `.WAV` ukuran ~400 MB + 1 `CONFIG.TXT`).
  2. **Skema 2:** Durasi 5 jam *nonstop* (menghasilkan 301 items: 300 file `.WAV` + 1 `CONFIG.TXT`).
* **Hasil:** Total panen data dari kedua skema *heterogeneous workload* berhasil diamankan.
* **Kendala:** Tidak ada kendala berarti. Kondisi di sekitar lokasi Kebun Raya terpantau sepi, sehingga perangkat aman dari gangguan fisik.
* **Keputusan:** Seluruh data di-*backup* ke *local storage*, Micro SD dikosongkan (*clean*) untuk persiapan hari terakhir.

---

### Entri: 25 September 2026
* **Lokasi & Kegiatan:** Embung D – *Deployment* AudioMoth hari terakhir.
* **Hasil:** Pengambilan data berjalan lancar, seluruh file `.WAV` dan `CONFIG.TXT` berhasil diamankan.
* **Kendala:** Tidak ada kendala lapangan. Situasi sangat aman dan kondusif.
* **Keputusan:** Fase pengumpulan data lapangan dari ketiga lokasi (Kantin, Kebun Raya, Embung D) resmi selesai. Data siap disatukan ke dalam direktori `data/raw/audiomoth/` untuk dilanjutkan ke tahap pembuatan manifes (*generate manifest*) menggunakan *script* Python.

## 6 Oktober 2026 - Penyelesaian Fase 0 (Kenali Lab)

### 1. Observasi Spesifikasi Lingkungan VM
Pengecekan dilakukan di dalam VM `dsic-lab-01` menggunakan perintah `cat /var/lib/dsic-lab/environment.txt`. Berikut adalah hasil observasi spesifikasi mesin:

| Komponen | Spesifikasi / Nilai |
| :--- | :--- |
| **Waktu Perekaman (UTC)**| `2026-10-06T07:44:08Z` |
| **Hostname** | `dsic-lab-01.asia-southeast2-a.c.sigerciv1.internal` |
| **Sistem Operasi** | Ubuntu 24.04.5 LTS |
| **Kernel** | `7.0.0-1013-gcp` |
| **Model CPU** | Intel(R) Xeon(R) CPU @ 2.20GHz |
| **Jumlah CPU (Core)** | 4 |
| **Total Memori** | 16.369.284 KB (~16 GB) |
| **Versi Docker** | Docker version 29.8.2, build 7fc2dff |
| **Versi Docker Compose**| Docker Compose version v5.6.0 |
| **Target Korpus Bucket** | `sigerciv1-dsic-2606-corpus` |
| **Direktori Data (Mount)**| `/dev/sdb ext4` |

**Catatan Temuan:**
Terdapat perubahan alokasi perangkat keras dari Google Cloud. Pada uji coba awal (5 Oktober 2026), prosesor yang terbaca adalah **AMD EPYC**. Namun, setelah mesin dihidupkan ulang pada sesi hari ini, prosesor berubah menjadi **Intel(R) Xeon(R)**. Temuan ini membuktikan profil ancaman validitas pada dokumen Fase 0, di mana metrik performa CPU berpotensi bervariasi antar-sesi eksperimen karena VM bersifat *on-demand*.

### 2. Pengujian Isolasi Data Korpus (Read-Only Access)
Pengujian dilakukan untuk membuktikan bahwa lingkungan eksperimen tidak dapat merusak data asli di dalam bucket.
*   **Perintah:** `echo uji | gcloud storage cp - gs://sigerciv1-dsic-2606-corpus/_uji_tulis`
*   **Hasil Output:** Gagal (Sesuai Ekspektasi)
    > `ERROR: (gcloud.storage.cp) [dsic-lab@...] does not have permission to access b instance... Permission 'storage.objects.create' denied on resource...`
*   **Kesimpulan:** VM hanya memiliki akses *read-only*. Upaya modifikasi atau penambahan file baru (`_uji_tulis`) ditolak secara paksa oleh sistem IAM Google Cloud, sehingga integritas data korpus suara burung dijamin aman dari anomali kode eksperimen.

## 6 Oktober 2026 — Fase 1: Seleksi Korpus Main dan Urutan Batch

* **Aturan seleksi:** File WAV yang ukurannya berbeda dari ukuran modal dikeluarkan dari subset eksperimen Main. File mentah tetap disimpan.
* **Sumber dan hasil seleksi:** Dari 301 WAV sumber, ukuran modal adalah 3.520.800 byte. Manifest eksperimen berisi 300 file. `20260924_183232.WAV` (488 byte) dikecualikan sesuai aturan ukuran. Pengecualian ini tidak dengan sendirinya menyimpulkan penyebab atau kondisi rekamannya.
* **Manifest dan batch:** `scripts/generate_manifest.py` menghasilkan `data/manifests/manifest_main.csv` dengan 300 rekaman. `scripts/freeze_batch_order.py` menghasilkan `data/batches/batch_order_main.csv` dengan 30 batch, masing-masing 10 rekaman.
* **Test:** `python -m unittest discover -s tests -v` — 9 test lulus, 0 gagal (0,102 detik).
* **Batas bukti saat ini:** Hasil ini berasal dari pemrosesan lokal. Pencocokan independen terhadap salinan korpus di VM/bucket, pembekuan `corpus.sha256`, dan pembuatan `expected_metadata.csv` belum dilakukan.
