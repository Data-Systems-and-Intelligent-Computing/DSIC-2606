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
* **Status saat catatan ini dibuat:** Hasil saat itu berasal dari pemrosesan lokal; pencocokan VM, pembekuan `corpus.sha256`, dan pembuatan `expected_metadata.csv` belum dilakukan. Hasil langkah-langkah lanjutan dicatat pada entri setelahnya.

**Pemeriksaan Pra-Unggah (Pre-Upload Check) - Korpus Main**
* Lokasi lokal: `data/raw/audiomoth/main/*.WAV`
* Jumlah berkas: 301 file
* Total ukuran: 1056240488 bytes
* Status izin bucket `gs://sigerciv1-dsic-2606-corpus/raw/main/`: Write/Append-only dikonfirmasi.

**Pemeriksaan Pasca-Unggah (Post-Upload Check) - Korpus Main**
* Perintah eksekusi: `gcloud storage cp --no-clobber ...`
* Verifikasi ukuran di bucket: 1.056.240.488 bytes (Cocok dengan lokal)
* Verifikasi jumlah file di bucket: 301 file (Cocok dengan lokal)
* Status Unggahan: Sukses 100%, integritas data terkonfirmasi, tidak ada upload parsial.

**Sinkronisasi dan Verifikasi VM (Lingkungan Lab) - Korpus Main**
* Perintah eksekusi: `gcloud storage rsync`
* Direktori eksperimen: `/data/corpus/main` (Berisi 300 file tervalidasi, ukuran ~1008 MB)
* Direktori pengecualian: `/data/corpus/dikeluarkan` (Berisi 1 file: `20260924_183232.WAV` / 488 byte)
* Status: Berkas mentah sukses disalin dari bucket sumber ke VM tanpa galat.

**Log Penggunaan VM (dsic-lab-01)**
* **Waktu Start:** 06 Oktober 2026, 21.54 WIB
* **Waktu Stop:** 07 Oktober 2026, 01.25 WIB (status `TERMINATED` dikonfirmasi pada 01:25:22 +07:00).
* **CPU Model:** Intel(R) Xeon(R) CPU @ 2.20GHz
* **Aktivitas:** Sinkronisasi korpus (rsync), isolasi anomali 488 byte, dan pengecekan environment.

**Verifikasi manifes terhadap salinan korpus di VM**
- Perintah: `python3 verify_corpus.py data/manifests/manifest_main.csv /data/corpus/main`
- Baris manifes: 300
- Berkas di disk: 300
- Hilang / berlebih / tidak cocok: 0 / 0 / 0
- Hasil: COCOK; kode keluar 0

**Langkah 4: Uji Negatif Verifikasi Korpus (Lingkungan VM)**
* **Waktu Eksekusi:** 07 Oktober 2026, 00.01 WIB
* **Perintah:** `python3 verify_corpus.py data/manifests/manifest_main.csv /data/work/uji-negatif`
* **Hasil:** TIDAK COCOK (Kode keluar: 1)
* **Status Uji:** SUKSES. Skrip verifikasi terbukti mampu mendeteksi berkas yang hilang (298 berkas) dan berkas yang korup/berubah ukuran (1 berkas).
* **Tindakan:** Direktori uji `/data/work/uji-negatif` dihapus.

**Pembekuan korpus Main di VM**
- `/data/corpus/main` dibuat tidak dapat ditulis dengan `sudo chmod -R a-w`.
- Dibuat `/data/work/DSIC-2606/data/manifests/corpus.sha256` menggunakan `sha256sum`.
- Jumlah baris checksum: 300.
- Folder uji negatif `/data/work/uji-negatif` dihapus setelah output disimpan.

Placeholder checksum_manifest.csv dan corpus_manifest.csv yang berukuran 0 byte dihapus setelah dipastikan tidak dirujuk skrip atau konfigurasi. Metadata dan hash per rekaman mengacu pada manifes masing-masing korpus; checksum beku Main dicatat di corpus.sha256.

## 7 Oktober 2026 — Pembaruan Fase 1: Metadata Acuan dan Provenans Perangkat

### Pembuatan `expected_metadata.csv`

- Skrip yang dijalankan: `python scripts/build_expected_metadata.py`.
- Sumber: `data/manifests/manifest_main.csv`.
- Baris manifest dibaca: 300; `recording_id` unik: 300.
- Baris yang ditulis ke `data/ground_truth/expected_metadata.csv`: 300.
- Kolom: `recording_id`, `device_id`, `start_time`, `object_uri`, `file_size_bytes`, `sha256`.
- Nilai `object_uri` dibentuk dari `expected_object_uri` pada manifest.
- Ground truth dibentuk dari manifest sebelum pipeline ingesti dijalankan; ia menjadi acuan rekonsiliasi, bukan hasil yang disalin dari keluaran pipeline.

### Provenans `CONFIG.TXT`

Empat konfigurasi sumber tersedia sebagai salinan di `data/manifests/device_provenance/`: `main_CONFIG.TXT`, `kantin_CONFIG.TXT`, `embungd_CONFIG.TXT`, dan `kebunraya_CONFIG.TXT`. Hash SHA-256 salinan diperiksa terhadap file konfigurasi sumber; keempatnya cocok.

| Sesi | Device ID fisik | Firmware | Jadwal lokal (UTC+7) | WAV pertama yang diperiksa |
|---|---|---|---|---|
| Main | `242A260460377E01` | `AudioMoth-Firmware-Basic (1.12.1)` | 13:30–18:30, 24 September 2026 | `20260924_133000.WAV` |
| Kantin | `242A260460377E01` | `AudioMoth-Firmware-Basic (1.12.1)` | 10:00–12:00, 23 September 2026 | `20260923_100000.WAV` |
| Embung D | `242A260460377E01` | `AudioMoth-Firmware-Basic (1.12.1)` | 12:10–13:50, 25 September 2026 | `20260925_121000.WAV` |
| Kebun Raya | `242A260460377E01` | `AudioMoth-Firmware-Basic (1.12.1)` | 11:10–12:50, 24 September 2026 | `20260924_111000.WAV` |

Keempat `CONFIG.TXT` mencatat Device ID fisik yang sama, sehingga jumlah perangkat fisik berdasarkan konfigurasi yang diperiksa adalah **1**. Semuanya mencatat `Use device ID in WAV file name: No`; nama WAV tidak menyertakan ID fisik.

Pak Dika mengonfirmasi pada 23 September 2026 bahwa waktu perangkat saat perekaman adalah waktu lokal UTC+7. Karena itu generator membaca timestamp nama file sebagai `Asia/Jakarta` dan menormalkannya ke UTC. Pada manifest Main, WAV pertama `20260924_133000.WAV` direpresentasikan sebagai `2026-09-24T06:30:00Z`.

Kolom manifest `device_id` tetap berisi label sesi, misalnya `MAIN_5JAM`. Aturan `recording_id` saat ini menggabungkan label sesi dan nama dasar file; Device ID fisik dicatat terpisah di `docs/device_provenance.md` dan tidak mengganti label sesi.

### Catatan waktu penggunaan VM

Setelah perintah stop, pemeriksaan status menampilkan `TERMINATED` pada 2026-10-07 01:25:22 +07:00 (WIB). Waktu ini dicatat sebagai waktu konfirmasi status berhenti, bukan sebagai timestamp persis transisi VM ke `TERMINATED`.




### Hasil test sebelum commit Fase 1

Pada 7 Oktober 2026, setelah manifest, batch order, checksum, dan expected metadata tersedia, test suite dijalankan dari akar repo lokal:

```text
python -m unittest discover -s tests -v
Ran 9 tests in 0.180s
OK
```

Seluruh 9 test lulus. Hasil ini merupakan keluaran yang dilaporkan pengguna.


## Penggunaan VM — 8 Oktober 2026 (persiapan Fase 2)

- **Pemeriksaan sebelum start:** Pada 16:45:38 WIB, status VM tercatat `TERMINATED`.
- **Start VM:** Perintah `gcloud compute instances start dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` berhasil; pemeriksaan sesudahnya menunjukkan status `RUNNING`.
- **Waktu start:** Waktu persis perintah start tidak tercatat. Berdasarkan pemeriksaan sebelum start dan waktu snapshot environment, start terjadi setelah 16:45:38 dan paling lambat 16:46:56 WIB. Waktu snapshot bukan waktu start yang persis.
- **Waktu snapshot environment:** `2026-10-08T09:46:56Z` (16:46:56 WIB).
- **Hostname:** `dsic-lab-01.asia-southeast2-a.c.sigerciv1.internal`.
- **OS / kernel:** Ubuntu 24.04.5 LTS / `7.0.0-1013-gcp`.
- **Model CPU:** Intel(R) Xeon(R) CPU @ 2.20GHz; 4 CPU.
- **Memori host:** 16.369.276 KB.
- **Docker / Compose:** Docker 29.8.2 (build `7fc2dff`) / Docker Compose v5.6.0.
- **Aktivitas:** Menyalakan VM untuk persiapan Fase 2 dan membaca `/var/lib/dsic-lab/environment.txt`.
- **Status instrumen lab:** Stack lab dijalankan pada sesi ini; `sudo make up` dan `sudo make ps` berhasil. `sudo make check` menemukan selisih digest image MinIO; rinciannya dicatat pada entri pemeriksaan Fase 2 di bawah.
## 8 Oktober 2026 — Pemeriksaan awal lingkungan Fase 2

- **Lokasi:** VM `dsic-lab-01`, direktori instrumen `/data/lab/dsic-lab-stack/`.
- **`sudo make up`:** berhasil; network Compose dibuat dan layanan MinIO, katalog, Spark master, serta Spark worker dijalankan. `minio-init` juga dijalankan.
- **`sudo make ps`:** katalog dan MinIO berstatus `healthy`; Spark master dan worker berstatus `Up`; `minio-init` berstatus `Exited (0)` setelah tugas inisialisasi selesai.
- **`sudo make check`:** gagal dengan kode keluar 1 karena satu selisih digest image MinIO. Keluaran membandingkan baris berikut:
  - sisi pertama keluaran diff: `minio | dsic-lab/minio:RELEASE.2025-04-22T22-12-26Z | sha256:26ae83b1a100a05d93b1ea33ae59a8526ac5ac91857fbc3b8e7f14422bf3d770`
  - sisi kedua keluaran diff: `minio | dsic-lab/minio:RELEASE.2025-04-22T22-12-26Z | sha256:d3af640a728fc086d56fa05829079f368c796ce08e2c207a0dfeb70c8b0aed2c`
- **Kesimpulan sementara:** layanan berhasil menyala, tetapi kesamaan lingkungan dengan `environment.lock.txt` belum terverifikasi karena digest MinIO berbeda. Nilai tidak diubah manual; tindak lanjut menunggu arahan pembimbing.
- **`sudo make selftest`:** belum dijalankan karena pemeriksaan `make check` gagal.
- **Waktu stop VM:** 8 Oktober 2026, 18:52:06 WIB. Perintah `gcloud compute instances stop dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` selesai; pemeriksaan status sesudahnya menunjukkan `TERMINATED`.
- **Penurunan stack:** menurut catatan pengguna, `sudo make down` dijalankan sebelum keluar dari sesi SSH. Keluaran perintah tidak tersimpan di catatan ini.
### Sesi VM lanjutan — 8 Oktober 2026 (validasi ulang Fase 2)

- **Waktu pencatatan sebelum start:** 22:10:00 WIB (`2026-10-08 22:10:00 +07:00`).
- **Start VM:** Perintah `gcloud compute instances start dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` berhasil.
- **Status setelah start:** `RUNNING`.
- **Snapshot environment:** `2026-10-08T15:10:53Z` (22:10:53 WIB), dari `/var/lib/dsic-lab/environment.txt`.
- **Hostname:** `dsic-lab-01.asia-southeast2-a.c.sigerciv1.internal`.
- **OS / kernel:** Ubuntu 24.04.5 LTS / `7.0.0-1013-gcp`.
- **Model CPU:** Intel(R) Xeon(R) CPU @ 2.20GHz; 4 CPU.
- **Memori host:** 16.369.272 KB.
- **Docker / Compose:** Docker 29.8.2 (build `7fc2dff`) / Docker Compose v5.6.0.
- **Data mount:** `/dev/sdb ext4`; bucket korpus: `sigerciv1-dsic-2606-corpus`.
### Tindak lanjut Fase 2 — klarifikasi digest dan hasil self-test (8 Oktober 2026)

- **Klarifikasi pembimbing 1 atas selisih sebelumnya:** image MinIO terbangun dua kali. Menurut pemeriksaan lab, manifest image dan SHA-256 biner MinIO sama; ID image berbeda karena memuat catatan waktu build. `environment.lock.txt` sebelumnya merekam ID dari image pertama, yang sudah tidak ada setelah kontainernya dihapus. Lab merekam ulang berkas kunci dan mengujinya setelah VM dimatikan lalu dinyalakan kembali. Catatan kegagalan awal di atas dipertahankan sebagai riwayat; klarifikasi ini merupakan tindak lanjutnya.
- **Identitas isi MinIO untuk pelaporan:** commit sumber `0d7408fc9969caf07de6a8c3a84f9fbb10a6739e`; SHA-256 biner `/out/minio`: `b8f3ba2fe46a637f962cfc5c2232b56590924fee94e3388bc0ead60a281204cb`. Mengikuti arahan Pak Dika, identitas isi dilaporkan dengan commit sumber dan hash biner, bukan ID image.
- **Perintah self-test:** `sudo make selftest` di `/data/lab/dsic-lab-stack/`.
- **Hasil:** `SELFTEST: lulus=27 gagal=0`.
- **Cakupan yang dilaporkan lulus:** pemeriksaan awal/reset dan preflight; deteksi selisih batas memori worker; deteksi objek/checkpoint/entri katalog tersisa; pemeriksaan multipart; penolakan korpus yang diubah pada salinan; perilaku checkpoint ephemeral dan persistent; harness SIGKILL; smoke test saat MinIO mati; serta kecocokan lock setelah kontainer dibuat ulang dan pada keadaan akhir.
- **T2 — Uji negatif reset:** `verify-only` menolak sisa satu objek MinIO, sisa checkpoint persistent, dan satu entri katalog; reset penuh setelahnya lulus membersihkan keadaan uji.
- **T3 — Pemeriksa multipart/ETag:** tanpa objek, pemeriksa tidak menyatakan lulus (kode 2); objek single-part 3.520.800 byte lulus; objek uji multipart 6 MiB terdeteksi di `_uji_instrumen/multipart.bin` dengan ETag `"7d368e72ecdd3ff1d9b28f29481a125f-2"`.
- **T4 — Uji negatif preflight pada salinan:** salinan utuh lulus; penambahan satu byte ke `20260924_133000.WAV` ditolak karena hash berbeda; penambahan berkas WAV asing ditolak karena jumlah berkas tidak cocok dengan `corpus.sha256`.
- **Batas uji:** perubahan korpus dilakukan pada salinan dan unggahan multipart memakai objek uji instrumen, bukan WAV korpus eksperimen.
- **Pemeriksaan lock di dalam self-test:** T0b dan T8b lulus; T9 juga menyatakan `down lalu up: check tetap lulus`.
- **Makna cakupan:** ini validasi instrumen dan lingkungan Fase 2. Self-test bukan eksekusi perlakuan penelitian B0/B1 pada korpus eksperimen.
