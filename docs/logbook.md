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

### Pengakhiran sesi validasi Fase 2 — 9 Oktober 2026

- **Hasil self-test sesi:** `SELFTEST: lulus=27 gagal=0`.
- **Penurunan stack:** pengguna melaporkan menjalankan `sudo make down` sebelum sesi SSH tertutup, tetapi keluarannya tidak tersimpan. Karena itu, keberhasilan penurunan stack tidak dapat diverifikasi dari output perintah.
- **Penghentian VM:** perintah `gcloud compute instances stop dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` selesai.
- **Waktu konfirmasi berhenti:** 9 Oktober 2026, 00:38:57 WIB (`2026-10-09 00:38:57 +07:00`); pemeriksaan status menampilkan `TERMINATED`. Ini waktu konfirmasi status, bukan waktu transisi VM yang persis.

### Sesi VM — 9 Oktober 2026 (awal pengerjaan Fase 3)

* Pemeriksaan sebelum start: [isi waktu dan status VM sebelum start bila sempat dicek; hapus baris ini bila tidak ada]
* Start VM: VM dinyalakan dengan `gcloud compute instances start dsic-lab-01 --zone asia-southeast2-a --project sigerciv1`. VM dapat diakses lewat SSH dan `/var/lib/dsic-lab/environment.txt` terbaca.
* Waktu start: 2026-10-09 11:00:08 WIB (2026-10-09T04:00:08Z), dari `lastStartTimestamp` pada `gcloud compute instances describe`. GCP menampilkan nilai ini dalam zona −07:00 (`2026-10-08T21:00:08.113-07:00`).
* Waktu snapshot environment: `2026-10-09T04:00:42Z` (11:00:42 WIB), 34 detik setelah start.
* Hostname: `dsic-lab-01.asia-southeast2-a.c.sigerciv1.internal`.
* OS / kernel: Ubuntu 24.04.5 LTS / `7.0.0-1013-gcp`.
* Model CPU: Intel(R) Xeon(R) CPU @ 2.20GHz; 4 CPU. Sama dengan sesi 8 Oktober.
* Memori host: 16.369.276 KB. Sama dengan sesi 8 Oktober.
* Docker / Compose: Docker 29.8.2 (build `7fc2dff`) / Docker Compose v5.6.0.
* Aktivitas: Menyalakan VM untuk melanjutkan Fase 2, membaca `/var/lib/dsic-lab/environment.txt`, dan menjalankan stack lab.
* Sinkronisasi repo VM: `git pull --ff-only` berhasil. Repo berada pada commit `b98358f` (`feat: define B0 and B1 checkpoint semantics`) dan sejajar dengan `origin/main`. File lokal `verify_corpus.py` berstatus belum dilacak dan tetap dipertahankan.
* Status instrumen lab:
  * `sudo make up` berhasil.
  * `sudo make ps`: `catalog` dan `minio` berstatus healthy; `spark-master` dan `spark-worker` Up; `minio-init` berstatus Up kurang dari satu detik saat `make ps` dijalankan.
  * Image yang terlihat di `make ps` (tag, bukan digest; digest acuan ada di `environment.lock.txt`): `postgres:16.4`, `dsic-lab/minio:RELEASE.2025-04-22T22-12-26Z`, `dsic-lab/spark:3.5.3-iceberg1.6.1`.
  * `sudo make check` lulus dengan keluaran `lingkungan sama dengan environment.lock.txt`.
* Waktu konfirmasi berhenti: 9 Oktober 2026, 12:32:36 WIB (`2026-10-09 12:32:36 +07:00`); perintah stop selesai dan status VM terkonfirmasi `TERMINATED`.

### Sesi VM — 14 Oktober 2026 (persiapan uji urutan event Fase 3)
- **Start VM**: Perintah `gcloud compute instances start dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` berhasil; status sesudah start RUNNING.
- **Waktu start**: Menurut Google Cloud: 2026-10-14T03:11:35.069-07:00, setara dengan 14 Oktober 2026, 17:11:35 WIB (2026-10-14T10:11:35.069Z).
- **Snapshot environment**: `2026-10-14T10:12:09Z` (14 Oktober 2026, 17:12:09 WIB), dibaca dari `/var/lib/dsic-lab/environment.txt`.
- **Model CPU**: Intel(R) Xeon(R) CPU @ 2.20GHz; 4 CPU.
- **Lingkungan**: Ubuntu 24.04.5 LTS, kernel `7.0.0-1013-gcp`, memori 16.369.268 KB; Docker 29.8.2 (build `7fc2dff`) dan Compose v5.6.0.
  ```text
  captured_utc=2026-10-14T10:12:09Z
  hostname=dsic-lab-01.asia-southeast2-a.c.sigerciv1.internal
  kernel=7.0.0-1013-gcp
  os=Ubuntu 24.04.5 LTS
  cpu_model=Intel(R) Xeon(R) CPU @ 2.20GHz
  cpu_count=4
  mem_total_kb=16369268
  docker=Docker version 29.8.2, build 7fc2dff
  compose=Docker Compose version v5.6.0
  corpus_bucket=sigerciv1-dsic-2606-corpus
  data_mount=/dev/sdb ext4
  ```
- **Pemeriksaan layanan pada sesi ini:** `sudo make up` berhasil. `sudo make ps` menunjukkan `catalog` dan `minio` healthy serta `spark-master` dan `spark-worker` Up; `minio-init` masih `Up Less than a second` saat status diambil.
- **Pemeriksaan lock:** `sudo make check` lulus dengan keluaran `lingkungan sama dengan environment.lock.txt`.
- **Uji urutan sumber file Spark (probe dummy):** Tiga event JSON berisi masing-masing 10 ID dummy disiapkan di `/data/results/source-order-probe-20261014/events`. Urutan nama file adalah `event-01.json`, `event-02.json`, `event-03.json`, sedangkan waktu modifikasinya berturut-turut 10:03, 10:01, dan 10:02 UTC.
- **Percobaan cluster awal:** Gagal dengan `SparkFileNotFoundException` untuk `/results/.../event-02.json`. Pemeriksaan mount menunjukkan worker hanya memiliki `/data/corpus/main -> /data/raw`, tidak memiliki mount `/results`. Percobaan ini tidak dipakai sebagai bukti urutan.
- **Probe lokal berhasil:** `PROBE_MASTER=local[2]`, `maxFilesPerTrigger=1`. Keluaran: micro-batch 0 membaca `event-02.json` (`event_batch=2`); micro-batch 1 membaca `event-03.json` (`event_batch=3`); micro-batch 2 membaca `event-01.json` (`event_batch=1`). Pada konfigurasi probe ini, urutan yang diamati mengikuti waktu modifikasi paling awal, bukan urutan nama file.
- **Implikasi rancangan replay:** Agar urutan batch eksperimen tidak bergantung pada pengurutan file, rencana replay adalah menyediakan satu event batch terlebih dahulu dan baru menyediakan event berikutnya setelah batch sebelumnya tercatat selesai. Probe ini hanya memakai JSON dummy dan Spark lokal; bukan eksekusi B0/B1 atau pemrosesan korpus WAV.

### Sesi VM lanjutan — 14 Oktober 2026 (Fase 3)

- **Waktu start terakhir:** 14 Oktober 2026, 22:09:17 WIB. Diambil dari `lastStartTimestamp` Google Cloud dan dikonversi ke UTC+7.
- **Snapshot environment:** `2026-10-14T15:09:56Z` (14 Oktober 2026, 22:09:56 WIB), dari `/var/lib/dsic-lab/environment.txt`.
- **Hostname:** `dsic-lab-01.asia-southeast2-a.c.sigerciv1.internal`.
- **OS / kernel:** Ubuntu 24.04.5 LTS / `7.0.0-1013-gcp`.
- **Model CPU:** Intel(R) Xeon(R) CPU @ 2.20GHz; 4 CPU.
- **Memori host:** 16.369.284 KB.
- **Docker / Compose:** Docker 29.8.2 (build `7fc2dff`) / Docker Compose v5.6.0.
- **Data mount / bucket:** `/dev/sdb ext4` / `sigerciv1-dsic-2606-corpus`.
- **Aktivitas:** Melanjutkan persiapan Fase 3. Belum ada eksekusi B0/B1 atau unggah WAV yang dilaporkan pada sesi ini.

### Adendum sesi VM — 14 Oktober 2026 (setelah snapshot environment)

- Setelah snapshot pukul 22:09:56 WIB, pengguna melaporkan mengunggah 300 WAV secara manual dari `/data/corpus/main` ke bucket MinIO `audiomoth`, pada prefix manifest `MAIN_5JAM/2026-09-24/`. Skrip melaporkan 300 objek terverifikasi, total 1.056.240.000 byte, `HASIL: COCOK` berdasarkan ukuran dan SHA-256.
- `sudo make verify-multipart` memeriksa 300 objek dan melaporkan 0 objek multipart. Keluaran berhasil disimpan di VM sebagai `/data/results/verify-multipart-20261014.log`; percobaan pertama menyimpan dengan `tee` tanpa `sudo` gagal karena izin, lalu berhasil dengan `sudo tee`.
- Unggah manual dan pemeriksaan multipart ini bukan eksekusi ingest B0/B1. Belum ada eksekusi F0 atau penulisan metadata Iceberg yang dilaporkan.
- Rincian perintah, keluaran, dan batas bukti kode unggah dicatat di [bukti sesi Fase 3 14 Oktober](phase3-session-20261014-evidence.md). Heredoc Boto3 yang ditempel ke percakapan terpotong, sehingga kode unggah lengkap tidak direkonstruksi.
- Sebelum reset atau ingest F0, perlu mengikuti protokol reset dan memastikan penanganan objek unggah manual dengan pembimbing.

### Pengakhiran sesi VM — 15 Oktober 2026

- Perintah stop VM: `gcloud compute instances stop dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` berhasil.
- Waktu konfirmasi setelah perintah stop: 15 Oktober 2026, 01:27:54 WIB (`2026-10-15 01:27:54 +07:00`).
- Status VM setelah stop: `TERMINATED`.
- Keluaran `sudo make down` tidak disertakan dalam catatan sesi; keberhasilan penurunan stack tidak diverifikasi dari keluaran yang tersedia.

### Sesi VM lanjutan — 15 Oktober 2026 (bukti unggah manual)

- **Waktu sebelum start:** 13:23:31 WIB (`2026-10-15 13:23:31 +07:00`), menurut `Get-Date` di PowerShell. Waktu transisi start yang persis belum diambil dari `lastStartTimestamp`.
- **Start dan status:** Perintah `gcloud compute instances start dsic-lab-01 --zone asia-southeast2-a --project sigerciv1` berhasil; sesudahnya VM dapat diakses melalui SSH dan status GCP menunjukkan `RUNNING`.
- **Snapshot environment:** `2026-10-15T06:24:29Z` (13:24:29 WIB). CPU Intel(R) Xeon(R) CPU @ 2.20GHz; 4 CPU; memori 16.369.284 KB; Ubuntu 24.04.5 LTS, kernel `7.0.0-1013-gcp`; Docker 29.8.2 (build `7fc2dff`), Compose v5.6.0.
- **Layanan:** `sudo make up` dan `sudo make ps` berhasil; `catalog` dan `minio` healthy, `spark-master` dan `spark-worker` Up. `sudo make check` lulus: `lingkungan sama dengan environment.lock.txt`.
- **Verifikasi objek sebelum reset:** `sudo make verify-multipart` memeriksa 300 objek dan melaporkan 0 objek multipart. Keluaran disimpan di VM pada `/data/results/verify-multipart-manual-20261015.log`.
- **Klien terpasang di VM:** Python Boto3 `1.34.46`, Botocore `1.34.46`, dari `python3` pada host VM. Ambang multipart yang benar-benar dipakai oleh skrip unggah manual belum terverifikasi; jangan mengisinya berdasarkan nilai bawaan.
- **Bukti yang masih perlu dikumpulkan:** daftar ETag per objek belum dicatat. Tidak ada reset atau eksekusi ingest yang dilaporkan pada sesi ini.
- Rincian perintah dan keluaran ada di [bukti sesi Fase 3](phase3-session-20261014-evidence.md).

#### Adendum — daftar ETag unggah manual

- Pengguna mengirim keluaran daftar ETag untuk prefix `MAIN_5JAM/2026-09-24/`; baris terakhir menyatakan `object_count=300`. Contoh baris yang dikirim berukuran 3.520.800 byte dan ETag berbentuk 32 karakter heksadesimal tanpa akhiran jumlah part.
- Pemeriksaan `verify-multipart` pada bucket yang sama melaporkan 300 objek diperiksa dan 0 multipart.
- Berkas daftar lengkap disimpan di VM sebagai `/data/results/etags-manual-20261015.tsv`.
- Bukti ini mendokumentasikan unggah manual sebelum reset, bukan unggah oleh pipeline B0/B1. Ambang multipart yang dipakai pada skrip unggah manual masih belum diketahui.
- Salinan bukti sudah diunduh ke repo lokal: `docs/evidence/etags-manual-20261015.tsv` dan `docs/evidence/verify-multipart-manual-20261015.log`. TSV berisi 300 baris objek, ditambah header dan penanda jumlah (`object_count=300`). Log menyatakan 300 objek diperiksa dan 0 multipart.

### Generator event replay — 15 Oktober 2026

- Menjalankan `python scripts/generate_batch_events.py --batch-order data/batches/batch_order_main.csv --output-dir data/replay/main/events` dari PowerShell.
- Keluaran: 30 batch, 10 ID per batch; folder output `data/replay/main/events`.
- Pemeriksaan manual: `event-000.json` berisi ID Main dari `20260924_133000` sampai `20260924_133900`; `event-029.json` berisi ID dari `20260924_182000` sampai `20260924_182900`.
- File event dibuat dari `batch_order_main.csv`; belum dijalankan oleh Spark dan belum menjadi bukti ingest B0/B1.
- Catatan integrasi: probe sebelumnya menunjukkan worker Spark tidak memiliki mount `/results`. Karena itu lokasi event untuk eksekusi cluster perlu dipastikan sebelum event ini dipakai.

#### Verifikasi event terhadap batch order — 15 Oktober 2026

Pengguna menjalankan pemeriksaan lokal yang membandingkan seluruh JSON event dengan `data/batches/batch_order_main.csv`. Keluaran yang dilaporkan:

```text
COCOK: 30 event, 300 recording_id sesuai batch_order_main.csv
```

Pemeriksaan ini hanya memvalidasi file replay lokal; belum menjalankan Spark atau ingest B0/B1.

### Persiapan konfigurasi Fase 3 — 15 Oktober 2026

- Konfigurasi batch dirapikan: `batching.yaml` menjadi satu-satunya sumber `ordering_rule` dan `batch_size`; jumlah Main diselaraskan menjadi 300 sesuai manifes/batch order eksperimen.
- `treatments.yaml` tidak lagi menyimpan pengaturan batch yang sama di blok `common`; test isolasi disesuaikan untuk membandingkan konfigurasi B0 dan B1 secara langsung.
- `docs/treatment-semantics.md` menjelaskan alasan B0 sebagai baseline at-least-once yang wajar dan tidak sengaja dilemahkan.
- Status spesifikasi Fase 2 sudah bertanda DRAFT, dan `software_manifest.yaml` sudah menyebut MinIO dibangun laboratorium dari sumber; keduanya diperiksa, tidak perlu diubah.
- Test belum dijalankan setelah perubahan ini; keluaran test akan dicatat setelah pengguna menjalankannya.

### Hari 2 — Pemeriksaan ulang korpus di Lightsail (30 Oktober 2026)

- **Lokasi pemeriksaan:** VM Lightsail, repo `/data/work/DSIC-2606`; korpus eksperimen `/data/corpus/main`.
- **Tujuan:** mencocokkan salinan korpus di Lightsail terhadap manifest dan `corpus.sha256` yang sudah dibekukan sebelumnya. Korpus tidak dibentuk ulang dan tidak diubah.
- **Jumlah WAV di korpus:** perintah `ls /data/corpus/main | wc -l` menghasilkan `300`.
- **Berkas dengan bit tulis untuk pemilik:** `find /data/corpus/main -type f -perm -u=w | wc -l` menghasilkan `0`.
- **Berkas yang dikeluarkan:** `/data/corpus/dikeluarkan/20260924_183232.WAV`, ukuran 488 byte. Berkas ini berada di luar direktori korpus eksperimen.
- **Pemeriksaan manifest:** `python3 verify_corpus.py data/manifests/manifest_main.csv /data/corpus/main` menghasilkan 300 baris manifest dan 300 berkas di disk; tidak ada berkas hilang, berlebih, atau tidak cocok; kode keluar `0`.
- **Pemeriksaan checksum beku:** `(cd /data/corpus/main && sha256sum -c --quiet /data/work/DSIC-2606/data/manifests/corpus.sha256)` tidak mencetak baris kegagalan dan kode keluar `0`.
- **Kesimpulan:** salinan korpus Main di Lightsail cocok dengan manifest dan checksum acuan. Hasil ini memvalidasi korpus sebelum eksperimen; bukan hasil ingest B0/B1.
- **Justifikasi:** pemeriksaan ini diulang setelah migrasi dari GCP untuk memastikan mesin baru membaca berkas WAV yang sama dengan acuan penelitian. Berkas 488 byte tetap dipisahkan sesuai aturan seleksi yang telah dicatat; tidak ada berkas korpus yang diubah.

Keluaran verifier yang dilaporkan:

```text
baris manifes : 300
berkas di disk: 300
hilang        : 0 []
berlebih      : 0 []
tidak cocok   : 0 []
HASIL: COCOK
kode keluar: 0
```

Keluaran pemeriksaan checksum yang dilaporkan:

```text
kode keluar: 0
```

#### Ringkasan angka korpus dari skrip — 30 Oktober 2026

- **Lokasi:** repo lokal `D:\TA\code TA\DSIC-2606`, PowerShell.
- **Perintah:** `python scripts/corpus_report.py`.
- **Sumber hitungan:** manifest Main dan batch order untuk subset eksperimen; Device ID unik dari empat salinan `CONFIG.TXT`; folder raw lokal untuk statistik sumber mentah.
- **Hasil subset Main:** 300 berkas, 1.056.240.000 byte, 1 perangkat fisik, rentang UTC `2026-09-24T06:30:00Z` sampai `2026-09-24T11:29:00Z`, 30 batch dengan 10 ID per batch, dan distribusi 300 berkas berukuran 3.520.800 byte.
- **Hasil korpus sumber mentah:** 301 berkas, 1.056.240.488 byte, rentang UTC `2026-09-24T06:30:00Z` sampai `2026-09-24T11:32:32Z`; terdiri dari satu berkas 488 byte dan 300 berkas 3.520.800 byte.
- Angka skrip cocok dengan ringkasan pada laporan korpus. Sumber mentah 301 berkas dan subset eksperimen 300 berkas dilaporkan terpisah karena `20260924_183232.WAV` dikeluarkan dari subset menurut aturan seleksi ukuran modal.
- Keluaran yang dikirim pengguna tidak memuat baris kode keluar; karena itu kode keluar skrip tidak dicatat.

### Validasi ground truth sebelum ingest — 30 Oktober 2026

- **Lokasi:** repo lokal `D:\TA\code TA\DSIC-2606`, PowerShell.
- **Tujuan:** memastikan `expected_metadata.csv` masih konsisten dengan manifest sebelum dipakai sebagai acuan hasil ingest.
- **Perintah:** `python scripts/validate_expected_metadata.py` dan `python -m unittest discover tests -v`.
- **Hasil validator:** 300 baris manifest, 300 baris expected metadata, selisih 0, `HASIL: COCOK`.
- **Hasil test:** 12 test lulus, 0 gagal. Test mencakup kecocokan ground truth, deteksi hash yang sengaja diubah pada salinan data uji, penolakan nama WAV bertimestamp tidak valid di direktori sementara, integritas manifest, identitas UTC, serta konfigurasi checkpoint B0/B1.
- **Batas bukti:** test dijalankan di PowerShell pada repo lokal, bukan di Lightsail. Versi Python tidak tercantum dalam keluaran yang dikirim. Ini memvalidasi acuan dan konfigurasi, belum membuktikan ingest B0/B1.

Keluaran validator yang dilaporkan:

```text
Baris manifest        : 300
Baris expected        : 300
Selisih               : 0
HASIL: COCOK
```

Keluaran test yang dilaporkan:

```text
test_expected_metadata_cocok_dengan_manifest (test_expected_metadata_consistency.ExpectedMetadataConsistencyTests) ... ok
test_perubahan_hash_di_salina_dideteksi (test_expected_metadata_consistency.ExpectedMetadataConsistencyTests) ... ok
test_nama_timestamp_invalid_ditolak_tanpa_membuat_manifest (test_generate_manifest_invalid_filename.GenerateManifestInvalidFilenameTests) ... ok
test_recording_id_tidak_kosong_dan_unik (test_manifest_integrity.ManifestIntegrityTests) ... ok
test_sha256_tidak_kosong_dan_formatnya_valid (test_manifest_integrity.ManifestIntegrityTests) ... ok
test_manifest_identity_uri_dan_utc_konsisten (test_stable_recording_id.StableRecordingIdentityTests) ... ok
test_naive_timestamp_digagalkan (test_stable_recording_id.StableRecordingIdentityTests) ... ok
test_b0_and_b1_differ_only_by_checkpoint_location (test_treatment_isolation.TreatmentIsolationConfigTests) ... ok
test_b0_resolves_to_ephemeral_path (test_treatment_isolation.TreatmentIsolationConfigTests) ... ok
test_b1_requires_a_persistent_root_and_resolves_per_run (test_treatment_isolation.TreatmentIsolationConfigTests) ... ok
test_checkpoint_roots_match_instrument (test_treatment_isolation.TreatmentIsolationConfigTests) ... ok
test_idempotence_is_off_for_both_treatments (test_treatment_isolation.TreatmentIsolationConfigTests) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.541s

OK
```
