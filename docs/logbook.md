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

### Rancangan perilaku F2 sebelum pilot — 2 November 2026

Catatan ini adalah prediksi sebelum uji, bukan hasil eksekusi. F2 adalah skenario ketika driver dihentikan pada titik kegagalan yang ditentukan, lalu pipeline dijalankan kembali untuk mengamati pemulihannya. Perilaku yang diperkirakan dicatat sebelum uji supaya hasil pilot dapat dibandingkan dengan prediksi, bukan dijelaskan setelah melihat hasil.

- **Landing replay:** pembimbing menetapkan akar disk host `/data/state/replay`, dipasang pada `/data/replay` di driver dengan akses baca-tulis dan di Spark worker hanya-baca. Setiap run memakai subfolder `/data/replay/<run_id>/`. Berkas event yang sudah dipublikasikan tetap berada di disk ketika kontainer driver berhenti. Mount ini masih menunggu pemasangan pembimbing; belum diverifikasi pada worker.
- **Aturan feeder setelah restart:** feeder memeriksa urutan berkas event yang sudah ada di landing. Jika berkas yang sudah dipublikasikan berurutan dari `event-000.json` sampai `event-k.json`, feeder tidak menyalinnya ulang dan melanjutkan publikasi dari `event-(k+1).json` setelah pemrosesan event tertunda dikenali selesai oleh Spark. Aturan feeder yang sama berlaku untuk B0 dan B1; tidak ada percabangan berdasarkan nama treatment.
- **Prediksi B0:** checkpoint berada di penyimpanan ephemeral dan hilang bersama kontainer driver. Berkas event lama tetap ada di landing, tetapi driver baru tidak memiliki progres checkpoint lama. Karena itu Spark dapat membaca ulang event yang masih tertinggal di landing. Dengan idempotence dimatikan, pemrosesan ulang dapat menambah baris metadata lagi; hal ini akan diperiksa, bukan diasumsikan sebagai hasil.
- **Prediksi B1:** checkpoint persisten tetap ada. Driver baru memakai checkpoint untuk menentukan progres stream dan melanjutkan dari progres yang tercatat. Event yang sudah ada di landing tetapi belum tercatat dalam progres checkpoint masih dapat dibaca ulang.
- **Batas bukti:** belum ada kegagalan F2 atau pemulihan yang dijalankan. Perbedaan B0/B1 di atas adalah prediksi berdasarkan daya tahan checkpoint; keluaran pilot dan jumlah duplikasi akan dicatat terpisah setelah pengujian.

### Pemeriksaan mount replay dan feeder lokal — 19–20 November 2026

Pada 19 November, setelah pembimbing menyatakan mount sudah disesuaikan, pemeriksaan dari Lightsail menunjukkan:

```text
dsic-lab-lock --status
bebas

./scripts/capture_env.sh --check
lingkungan sama dengan environment.lock.txt

/data/corpus/main -> /data/raw rw=false
/data/state/replay -> /data/replay rw=false

sha256sum environment.lock.txt
0b9e90778b884cba71efe1fd2c91110e6fe65bf69bfad90dd7362e2fb5686c12  environment.lock.txt
```

Konfigurasi Compose yang diperiksa memasang `/data/state/replay` ke `/data/replay` secara read-only pada worker dan read-write pada driver. Repo VM berada pada `f8ba12c`, sama dengan `origin/main`; masih ada berkas lokal tak terlacak `verify_corpus.py`, yang tidak dimasukkan ke commit ini. Pemeriksaan ini membuktikan kesiapan mount dan lock, bukan eksekusi replay Spark.

Pada 20 November, ditambahkan uji unit lokal untuk feeder replay: penerbitan event berikutnya hanya setelah batch selesai, pelestarian event saat objek feeder dibuat ulang, serta penolakan event bernomor bolong atau berisi jumlah ID yang salah. Seluruh suite lokal dijalankan:

```text
Ran 16 tests in 1.215s
OK
```

Keluaran lengkap tersimpan di `docs/evidence/unittest-20261120.txt`. Pada titik catatan ini, feeder belum terhubung ke `microbatch.py`; sambungan dan pipeline awal dicatat pada entri implementasi setelah ini. Belum ada run B0/F0 atau B1/F0.

### Implementasi awal alur ingest B0/B1 — 20 November 2026

- **Perubahan lokal:** `microbatch.py` kini membaca 30 event dan memvalidasi urutan serta 10 ID tiap event terhadap `batch_order_main.csv`. Feeder menerbitkan event berikutnya setelah micro-batch sebelumnya selesai dan checkpoint Spark tercatat.
- **Urutan penulisan per rekaman:** berkas sumber di `/data/raw` diverifikasi ukuran dan SHA-256-nya, lalu pipeline melakukan PUT ke bucket/key dari `expected_object_uri`, memakai boto3 1.35.36 dari image Spark dengan ambang dan ukuran part 5 MiB. PUT dianggap terkonfirmasi sesudah `upload_file` berhasil dan `HEAD` memeriksa ukuran serta metadata SHA-256. Sesudah itu satu baris metadata ditambahkan ke Iceberg; kembalinya `.append()` menandai batas commit. Keduanya punya catatan log terpisah.
- **Tabel metadata:** `lab.main.recordings` ditetapkan sebagai tabel eksperimen di `configs/ingestion.yaml`; `lab.smoke.t` tetap hanya tabel smoke test instrumen.
- **Pemeriksaan F0 yang disiapkan:** setelah 30 micro-batch, kode memeriksa 300 baris metadata unik yang cocok dengan manifest dan 300 object key yang cocok dengan URI manifest.
- **Feeder:** waktu modifikasi event landing dibuat meningkat sesuai nomor publikasi, supaya event yang menumpuk saat driver berhenti tetap disajikan sesuai urutan oleh sumber file Spark.
- **Test lokal:** `python -m unittest discover tests -v` lulus, 28 test, 0 gagal. Keluaran aktual disimpan di `docs/evidence/unittest-20261120-ingestion.txt`. Pemeriksaan sintaks Python dan `git diff --check` juga lulus.
- **Batas bukti:** ini baru validasi lokal. Boto3 MinIO dan Iceberg belum dijalankan lewat kontainer Spark di Lightsail; belum ada hasil B0/F0 atau B1/F0. Tabel serta bucket harus dimulai kosong sesuai preflight/reset lab sebelum pilot, dan keadaan lock harus diperiksa lebih dahulu.

### Pilot B0/F0 pada Lightsail — 19–20 November 2026

- **Commit yang dijalankan:** `392893d` (`feat: implement B0 B1 ingestion pipeline`), ditarik di VM sebelum pilot.
- **Run:** `TREATMENT=B0`, `FAULT=F0`, `RUN_ID=b0-f0-20261120`; kode keluar 0.
- **Konfigurasi efektif:** checkpoint `/checkpoints/ephemeral/b0-f0-20261120/B0`; `maxFilesPerTrigger=1`; 30 event × 10 ID; metadata Iceberg di `lab.main.recordings`; idempotence `false`.
- **Hasil rekonsiliasi:** 300 objek, 300 baris metadata, 300 ID rekaman unik, dan 300 pemeriksaan HEAD ukuran serta metadata SHA-256 lulus.
- **Urutan replay:** pemeriksa mencocokkan 30 batch × 10 ID dengan `batch_order_main.csv`.
- **Multipart:** 300 objek diperiksa; 0 objek multipart. Klien pipeline boto3 1.35.36 dari image Spark; ambang dan ukuran part 5 MiB.
- **ETag:** daftar 300 rekaman unik tersimpan di `docs/evidence/etags-b0-f0-20261120.tsv`. Keluaran mentah disimpan bersama log run, hasil pemeriksaan batch, dan hasil multipart di `docs/evidence/`.
- **CPU sesi VM:** `Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz`; dikonfirmasi dengan `lscpu` pada 2026-11-19 20:40:39 UTC. Waktu boot `2026-10-17 14:19:30 UTC`, sebelum eksekusi B0.
- **Status Fase 3:** B0/F0 berhasil. B1/F0, perbandingan konfigurasi efektif dua run, dan bukti perilaku checkpoint setelah restart masih harus dikerjakan.

### Pilot B1/F0 dan restart checkpoint — 19–20 November 2026

- **Commit yang dijalankan:** `392893d`, sama dengan commit B0/F0.
- **Run:** `TREATMENT=B1`, `FAULT=F0`, `RUN_ID=b1-f0-20261120`; kode keluar 0.
- **Hasil rekonsiliasi:** 300 objek, 300 baris metadata, 300 recording ID unik, dan 300 pemeriksaan HEAD ukuran serta metadata SHA-256 lulus.
- **Urutan replay:** 30 batch × 10 ID cocok dengan `batch_order_main.csv`.
- **Multipart:** 300 objek diperiksa; 0 multipart.
- **Perbandingan konfigurasi efektif:** pemeriksa menyatakan `COCOK`; satu-satunya kunci yang berbeda antara B0 dan B1 adalah `checkpoint_location`.
- **Restart B1:** driver baru dijalankan kembali dengan run ID yang sama; kode keluar 0 dan rekonsiliasi tetap 300 objek/300 baris metadata. Direktori checkpoint persisten masih berisi `metadata`, `sources`, `offsets`, dan 30 commit bernomor.
- **CPU sesi:** `Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz`, diperiksa dengan `lscpu`; VM boot `2026-10-17 14:19:30 UTC`, sebelum run B0 dan B1.
- **Bukti mentah dan ringkasan:** disimpan di `docs/evidence/b1-f0-20261120.md` beserta log run, log restart, inventaris checkpoint, hasil pembanding konfigurasi, validasi batch, dan multipart.
- **Status Fase 3:** F0 B0/B1, kecocokan batch, konfigurasi efektif, multipart, dan daya tahan checkpoint B1 telah dibuktikan. Bukti eksplisit restart B0/checkpoint ephemeral masih perlu dipastikan.

### Restart B0/F0 dan bukti hilangnya checkpoint ephemeral — 20 November 2026

- **Pemeriksaan sebelum run:** `dsic-lab-lock --status` menghasilkan `bebas`; `sudo make check` menyatakan `lingkungan sama dengan environment.lock.txt`.
- **Anomali sebelum run:** setelah stack sempat dihentikan dan dinyalakan kembali, preflight menemukan 300 objek di `audiomoth` dan 1.201 objek di `warehouse`, meskipun reset sebelumnya sempat melaporkan bersih. Pemeriksaan isi `scripts/preflight.sh` menunjukkan pemeriksaan korpus dan `reset.sh --verify-only`; preflight tidak menghapus atau mengunggah objek. Reset ulang menghapus 300 dan 1.201 objek, memverifikasi kedua bucket nol, lalu B0 dijalankan tanpa menghentikan stack di antaranya.
- **Run B0/F0 baru:** `RUN_ID=b0-checkpoint-20261120`, kode keluar 0. Rekonsiliasi menunjukkan 300 objek, 300 baris metadata, 300 ID unik, dan 300 pemeriksaan HEAD. Konfigurasi efektif mencatat checkpoint `/checkpoints/ephemeral/b0-checkpoint-20261120/B0` dan 30 batch.
- **Restart attempt 2:** driver baru dijalankan dengan treatment dan RUN_ID sama, tanpa reset. Log menunjukkan 30 batch replay dan 300 append metadata. Audit F0 melaporkan `expected 300, found 600`, sehingga attempt keluar dengan kode 1. Ini hasil yang diharapkan untuk B0 tanpa checkpoint persisten dan tanpa idempotence: objek pada key yang sama tertimpa, sedangkan metadata append terduplikasi.
- **Pemeriksaan sesudah restart:** MinIO melaporkan 300 objek di `audiomoth` dan 2.401 objek di `warehouse`; angka warehouse menghitung berkas objek Iceberg, bukan baris metadata. Audit melaporkan 600 baris metadata. Direktori B0 tidak ada di akar checkpoint persisten `/data/state/checkpoints`; konfigurasi run menunjukkan checkpoint B0 berada pada tmpfs ephemeral driver.
- **Bukti mentah:** log initial run, log restart, ringkasan pemeriksaan checkpoint, log reset ulang, dan log pemeriksaan lock disimpan di `docs/evidence/`.
- **Status Fase 3:** perilaku checkpoint B0 setelah driver baru kini teramati dan cocok dengan sifat ephemeral. Bersama bukti B1 persisten yang telah dicatat sebelumnya, butir checkpoint restart sudah diuji. Tepat setelah run ini, hasil restart B0 masih berada di sink; keadaan tersebut kemudian dibersihkan dan self-test Hari 5 memastikan kembali keadaan akhir bersih (lihat entri Hari 5).

### RQ v1 untuk Gate Minggu 1 — 20 November 2026

- **Kegiatan:** menyusun `docs/rq-v1.md` dengan RQ1–RQ5 dan hipotesis H1–H4 berdasarkan bagian *Research Question* dan *Hipotesis* di `README.md`.
- **Perbandingan dokumen saat itu:** perbedaan dengan rumusan di `paper/manuscript.md` dicatat untuk ditinjau; keputusan D-03 belum tercatat pada entri awal ini.
- **Batas publikasi:** `docs/publication-boundary.md` dilengkapi dengan enam klaim yang tidak dibuat dan cakupan Gate Minggu 1. Pada saat pencatatan awal, dokumen masih berstatus draf.
- **Uji bahasa klaim:** `tests/test_claim_language.py` memindai `src/`, `paper/`, dan `results/` untuk frasa `exactly-once` atau `exactly once`. Test lulus pada isi repo, gagal dengan kode 1 ketika frasa terlarang sementara ditambahkan ke `paper/`, lalu lulus lagi setelah berkas probe dihapus. Keluaran asli tersimpan di `docs/evidence/claim-language-20261120.txt`.
- **Suite lengkap:** `python -m unittest discover tests -v` lulus: 30 test, 0 gagal, kode keluar 0. Keluaran aktual pada revisi ini tersimpan di `docs/evidence/unittest-gate-week1-20261120.txt`; validasi parse YAML untuk `configs/environment.yaml` dan `configs/ingestion.yaml` juga lulus.
- **Status pada entri awal:** RQ masih draf ketika catatan ini dibuat. Tidak ada klaim hasil eksperimen baru.

### Penyelarasan dokumen setelah keputusan D-03 / D-41 — 20 November 2026

- **Keputusan:** paket terbaru pembimbing mencatat bahwa D-03 menetapkan rumusan RQ di README sebagai acuan dan D-41 menutup Gate Minggu 1 secara bersyarat. Pak Dika mengizinkan dimulainya Minggu 2.
- **RQ dan manuskrip:** `docs/rq-v1.md` dan bagian pertanyaan penelitian di `paper/manuscript.md` diselaraskan dengan RQ1–RQ5 README; frasa tambahan perbandingan terhadap B0 pada RQ2 dihapus agar rumusannya sama dengan acuan.
- **Batas publikasi:** status `docs/publication-boundary.md` diubah dari DRAFT menjadi berlaku sesuai D-03. Klaim tetap dibatasi pada hasil *post-recovery correctness* dan *exact recovery* yang benar-benar diuji.
- **Gate:** laporan Gate Minggu 1 diperbarui untuk mencatat penutupan bersyarat D-41. Ini mengizinkan pekerjaan Minggu 2, tetapi tidak menyatakan hipotesis F1–F3 telah teruji.

### Hari 5 — Pemeriksaan lingkungan dan self-test di Lightsail — 20 November 2026

- **Status lock sebelum pemeriksaan:** `dsic-lab-lock --status` menghasilkan `bebas`.
- **Layanan:** `sudo make up` selesai; MinIO berstatus `healthy`, katalog `healthy`, Spark master dan worker `Up`. Keluaran `sudo make ps` disimpan bersama bukti Hari 5.
- **Lock lingkungan:** `sudo make check` menghasilkan `lingkungan sama dengan environment.lock.txt`.
- **Self-test:** koneksi SSH terputus ketika keluaran sedang berada di T7. Setelah masuk kembali, tidak ada proses self-test aktif dan lock berstatus `bebas`; log yang tersimpan menunjukkan test berlanjut sampai penutup. Hasil akhir: `SELFTEST: lulus=31 gagal=0`. Self-test tidak dijalankan ulang.
- **Cakupan yang terlihat pada keluaran:** reset bersih dan preflight lulus; uji negatif reset mendeteksi objek, checkpoint, event replay, dan entri katalog tersisa; uji multipart instrumen lulus; preflight menolak korpus salinan yang berubah atau berkas asing; perilaku checkpoint ephemeral/persistent dan mount replay diuji; harness SIGKILL dan smoke test saat MinIO mati lulus; akhir test bersih dan lock cocok.
- **Bukti mentah Lightsail:** `docs/evidence/week1-day5-up-20261120.log`, `week1-day5-ps-20261120.log`, `week1-day5-check-20261120.log`, dan `week1-day5-selftest-20261120.log`.

### Hari 2 — Konfirmasi ulang korpus beku di Lightsail — 20 November 2026

- **Waktu pemeriksaan:** `2026-11-20T10:49:24+00:00`.
- **Korpus:** `/data/corpus/main` berisi 300 berkas WAV dan 0 berkas dengan bit tulis untuk pemilik.
- **Verifikasi manifest:** `python3 verify_corpus.py data/manifests/manifest_main.csv /data/corpus/main` melaporkan 300 baris manifest, 300 berkas di disk, 0 hilang, 0 berlebih, 0 tidak cocok; `HASIL: COCOK`, kode keluar 0.
- **Verifikasi SHA-256:** `sha256sum -c --quiet` terhadap `data/manifests/corpus.sha256` berakhir dengan kode keluar 0.
- **Bukti mentah:** keluaran disimpan di VM pada `/data/results/week1-day2-corpus-20261120.log`, lalu disalin ke `docs/evidence/week1-day2-corpus-20261120.log` di repo lokal pada 20 November 2026. Ukuran berkas lokal 228 byte.

### Hari 1 — Snapshot lingkungan dan repo Lightsail — 20 November 2026

- **Waktu pemeriksaan:** `2026-11-20T10:57:20+00:00`; SSH masuk memakai akun `vania`.
- **Mesin:** `t3.xlarge`, `ap-southeast-2`, Ubuntu 24.04.4 LTS, kernel `7.0.0-1012-aws`, 4 vCPU, Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz; `dsic-lab-lock --status` menghasilkan `bebas`.
- **Memori dan disk saat diperiksa:** 15 GiB terdeteksi oleh `free -h`; `/dev/root` berukuran 309 GiB dengan 279 GiB tersedia. Nilai ini merupakan snapshot sesi, bukan spesifikasi tetap untuk seluruh eksperimen.
- **Repo sebelum sinkronisasi:** branch `main` di `c3a74dc`, status `behind 1`; ada berkas tak terlacak `verify_corpus.py` dan cache Python. Berkas tak terlacak dipertahankan.
- **Sinkronisasi repo:** `git pull --ff-only` berhasil fast-forward dari `c3a74dc` ke `c09b2f7`. Sesudahnya branch `main` sejajar dengan `origin/main`. Berkas tak terlacak `verify_corpus.py` dan cache Python tetap ada serta tidak diubah.
- **Bukti mentah:** snapshot awal tersimpan di VM pada `/data/results/week1-day1-lightsail-20261120.log`, lalu disalin ke `docs/evidence/week1-day1-lightsail-20261120.log` (1.560 byte). Keluaran pull/status akhir tersimpan di `/data/results/week1-day1-sync-20261120.log`, lalu disalin ke `docs/evidence/week1-day1-sync-20261120.log` (1.424 byte). Penyalinan diverifikasi dengan `Get-ChildItem` di PowerShell pada 20 November 2026.

### Hari 8 — Kebijakan idempotence dan implementasi lokal awal B2 — 20 November 2026

- **Keputusan checksum:** jika objek MinIO dengan URI manifest sudah ada, B2 memeriksa ukuran lewat HEAD lalu mengunduh byte objek secara streaming dan menghitung SHA-256 aktual. Header metadata SHA-256 objek tidak dianggap bukti isi. Satu replay dapat membaca kembali sekitar 1.056.240.000 byte; biaya baca ini diterima demi memeriksa konten sebenarnya.
- **Keputusan konflik:** ketidakcocokan ukuran/hash objek atau metadata menghentikan run dan tidak menimpa objek/baris lama. Baris metadata yang identik menjadi no-op. Event yang mengandung `recording_id` ganda ditolak sebelum penulisan ke sink.
- **Implementasi lokal:** ditambahkan guard objek berdasarkan URI manifest dan isi byte aktual serta upsert Iceberg `MERGE` berdasarkan `recording_id`. B2 diaktifkan dengan `idempotence_enabled: true` dan checkpoint ephemeral; B0/B1 tidak diubah. Konfigurasi kebijakan disimpan terpisah di `configs/idempotence.yaml`.
- **Test lokal:** `python -m unittest discover tests -v` lulus: 41 test, 0 gagal, kode keluar 0. Keluaran perintah disimpan di `docs/evidence/unittest-20261120-b2-local.txt`.
- **Probe sink di Lightsail:** dijalankan dengan commit `7c7e6a6`. PUT pertama lulus; pengulangan mengenali byte identik sebagai `SUDAH ADA`; checksum konflik tidak menimpa objek. MERGE pertama memasukkan satu baris, pengulangan identik menjadi no-op, dan metadata konflik tidak menimpa baris lama. Probe melaporkan tabel terhapus serta prefix objek dan warehouse kosong. Keluaran tersimpan di `docs/evidence/idempotence-sink-probe-7c7e6a6.log`.
- **B2/F0 di Lightsail:** `RUN_ID=b2-f0-20261120`, kode keluar 0. Log konfigurasi efektif mencatat `idempotence_enabled=true`, checkpoint ephemeral, `maxFilesPerTrigger=1`, dan 30 batch. Guard mencatat 300 keputusan `PUT`, 0 `SUDAH ADA`; terdapat 300 upsert metadata. Rekonsiliasi melaporkan 300 objek, 300 baris metadata, 300 ID unik, dan 300 pemeriksaan HEAD. Pemeriksa batch menyatakan 30 batch × 10 ID cocok dengan `batch_order_main.csv`. Pemeriksaan multipart menemukan 300 objek dan 0 multipart.
- **Bukti mentah:** log B2/F0, hasil pemeriksaan batch, dan multipart tersedia di `docs/evidence/b2-f0-20261120.log`, `verify-batches-b2-f0-20261120.txt`, serta `verify-multipart-b2-f0-20261120.log`.
- **Batas bukti:** uji sink dan F0 B2 berhasil, tetapi belum membuktikan perilaku B2 saat fault/restart atau hasil P1. Fase 4 masih berlanjut ke pengujian fault yang ditetapkan protokol; jangan menyimpulkan hasil hipotesis sebelum pengujian itu selesai.

### Hari 9 — Konfigurasi treatment P1 — 20 November 2026

- **Perubahan:** P1 ditambahkan sebagai kombinasi `idempotence_enabled: true` dan checkpoint persistent per-run. Kode ingest yang sama menangani B2/P1; pemilihan treatment tetap melalui konfigurasi, tanpa cabang nama treatment.
- **Audit pemisahan konfigurasi:** test kini membuktikan B0/B1 hanya berbeda pada checkpoint, B0/B2 dan B1/P1 hanya berbeda pada idempotence, serta B2/P1 hanya berbeda pada checkpoint.
- **Test lokal:** `python -m unittest discover tests -v` lulus: 45 test, 0 gagal, kode keluar 0. Keluaran aktual tersimpan di `docs/evidence/unittest-20261120-p1-local.txt`.
- **P1/F0 di Lightsail:** `RUN_ID=p1-f0-20261120`, kode keluar 0. Konfigurasi efektif mencatat idempotence aktif dan checkpoint `/checkpoints/persistent/p1-f0-20261120/P1`. Guard mencatat 300 PUT dan 0 `SUDAH ADA`; MERGE metadata tercatat 300 kali. Rekonsiliasi melaporkan 300 objek, 300 baris metadata, dan 300 ID unik. Pemeriksa batch menyatakan 30 batch × 10 ID cocok; multipart memeriksa 300 objek dan menemukan 0 multipart. Direktori checkpoint persistent ada dan berisi 30 commit bernomor.
- **Bukti mentah:** `docs/evidence/p1-f0-20261120.log`, `verify-batches-p1-f0-20261120.txt`, `verify-multipart-p1-f0-20261120.log`, dan `checkpoint-p1-f0-20261120.txt`.
- **Batas bukti:** P1/F0 dan isolasi treatment pada konfigurasi sudah dibuktikan. Perilaku B2/P1 saat fault/restart serta rekonsiliasi I1–I2 masih perlu dikerjakan.

### Hari 11 — Implementasi rekonsiliator I3–I5 — 21 November 2026

- **Perubahan:** ditambahkan penilai I3 referential, I4 orphan object, dan I5 dangling metadata. Pembaca metadata mengambil kolom yang diperlukan dari tabel Iceberg; pembaca objek memakai paginator `ListObjectsV2` untuk seluruh halaman pada bucket yang dirujuk ground truth.
- **Aturan perbandingan:** `s3://` dan `s3a://` dianggap setara; bucket dan object key harus identik. I3 juga membandingkan `device_id`, `file_size_bytes`, `sha256`, dan `start_time` ke ground truth sesuai semantik di `docs/correctness-invariants.md`. URI salah pada metadata menghasilkan I3 dan I5; objek asal yang tidak lagi dirujuk juga menghasilkan I4. Objek tambahan hanya memicu I4, sedangkan objek yang hilang dengan metadata tersisa hanya memicu I5.
- **Test lokal:** `python -m unittest discover tests -v` lulus: 60 test, kode keluar 0. Test baru memeriksa kasus I3–I5 dan paginasi pembaca objek. Keluaran tersimpan di `docs/evidence/unittest-20261121-i3-i5-local.txt`.
- **Batas bukti saat Hari 11:** implementasi I3–I5 baru diuji lokal; audit VM baca-saja dan uji keadaan rusak masih diperlukan. I6–I7 dikerjakan pada Hari 12.

### Hari 12 — Rekonsiliator I1–I7 dan Exact Recovery — 21 November 2026

- **Perubahan:** ditambahkan I6 yang mengunduh objek acuan yang tercantum di listing dan menghitung SHA-256 aktual per potongan 1 MiB, serta membandingkan ukuran/hash dengan expected metadata. I7 melaporkan recording ID metadata yang tidak terdapat di ground truth.
- **Hasil rekonsiliasi:** CLI sekarang menggabungkan I1–I7, melaporkan jumlah byte yang di-hash dan durasi lengkap audit, serta menetapkan `exact_recovery=true` hanya jika semua tujuh invariant lulus. Schema keluaran di `schemas/reconciliation_result.schema.json` sudah diisi.
- **Test lokal:** `python -m unittest discover tests -v` lulus: 67 test, kode keluar 0. Cakupan mencakup I6/I7, hash stream per potongan, integrasi evaluator I1–I7, dan validasi hasil contoh terhadap schema. Keluaran tersimpan di `docs/evidence/unittest-20261121-reconciliation-i1-i7-local.txt`.
- **Audit bersih P1/F0 di Lightsail:** `I1_I7_RECONCILIATION` menghasilkan `all_pass=true` dan `exact_recovery=true`. Dari 300 ID/objek yang diharapkan, tidak ada ID hilang, duplikat, metadata tambahan, objek yatim, metadata menggantung, atau ketidakcocokan metadata/byte. Ketujuh invariant lulus; 300 objek (1.056.240.000 byte) diunduh dan di-hash, durasi audit 56,772 detik.
- **Bukti VM:** log mentah `docs/evidence/reconciliation-i1-i7-p1-f0-20261120.log` (disalin dari `/data/results/reconciliation-i1-i7-p1-f0-20261120.log`). Audit ini hanya membaca keadaan P1/F0; tidak menguji fault/restart dan tidak mengubah sink.
- **Batas bukti:** audit I1–I7 bersih ini baru untuk P1/F0. B0/F0, B1/F0, dan B2/F0 belum diaudit dengan rekonsiliator lengkap versi I1–I7; uji keadaan nyata yang dirusak juga masih perlu dilakukan sebelum rangkaian E0 empat treatment dinyatakan selesai.

### Hari 10 — Reconciliation metadata I1–I2 — 21 November 2026

- **Implementasi lokal:** ditambahkan evaluator completeness dan uniqueness. I1 membandingkan ID ground truth dengan ID pada tabel dan melaporkan missing count/rate. I2 melaporkan jumlah ID logis yang duplikat, kelebihan baris duplikat, dan baris dengan `recording_id` kosong. Ground truth kosong atau memiliki ID duplikat ditolak.
- **Audit Spark P1/F0 di Lightsail:** dijalankan terhadap `lab.main.recordings`; proses Spark berhenti dengan exit code 0. Ringkasan `I1_I2_RECONCILIATION` menyatakan `all_pass=true`: 300 ID yang diharapkan, 300 baris metadata aktual, 300 ID unik, 0 ID hilang, 0 duplikat, dan 0 baris dengan ID kosong.
- **Test lokal:** `python -m unittest discover tests -v` lulus: 51 test, 0 gagal, kode keluar 0. Test baru mencakup keadaan lulus, missing ID, metadata duplikat, dan ID aktual kosong. Keluaran tersimpan di `docs/evidence/unittest-20261121-reconciliation-i1-i2-local.txt`.
- **Bukti VM:** log audit mentah tersimpan di `docs/evidence/reconciliation-i1-i2-p1-f0-20261121.log` (33.166 byte).

### Audit ulang B0/F0 untuk perbandingan E0 — 21 November 2026

- **Keadaan awal dan eksekusi:** `make reset` berakhir dengan `reset bersih`, lalu B0/F0 dijalankan dengan `RUN_ID=e0-b0-20261121`. Ingest selesai dengan kode keluar 0 dan 30 batch.
- **Audit setara:** hasil `I1_I7_RECONCILIATION` menyatakan `all_pass=true` dan `exact_recovery=true`. Terdapat 300 objek, 300 baris metadata, 300 recording ID unik, dan 300 URI objek unik.
- **Rincian invariant:** I1 tidak menemukan ID hilang; I2 tidak menemukan ID duplikat atau kosong; I3 tidak menemukan metadata yang berbeda dari ground truth; I4 tidak menemukan objek yatim; I5 tidak menemukan metadata tanpa objek; I6 memeriksa SHA-256 seluruh 300 WAV (1.056.240.000 byte) tanpa mismatch; I7 tidak menemukan baris metadata tambahan.
- **Durasi audit:** 54,963 detik. Audit I1–I7 ini membaca hasil B0/F0 setelah ingest; bukan pengujian fault/restart.
- **Bukti mentah:** `docs/evidence/e0-b0-f0-20261121.log` (2.408.424 byte), berisi keluaran reset, ingest, dan audit.
- **Status perbandingan E0:** B0/F0 sudah diulang dari keadaan bersih dan diaudit dengan I1–I7. B1/F0 dan B2/F0 masih perlu dijalankan ulang dan diaudit dengan cara yang sama agar perbandingannya setara.

### Audit ulang B1/F0 untuk perbandingan E0 — 21 November 2026

- **Keadaan awal dan eksekusi:** `make reset` berakhir dengan `reset bersih`, lalu B1/F0 dijalankan dengan `RUN_ID=e0-b1-20261121`. Ingest selesai dengan kode keluar 0 dan 30 batch.
- **Audit setara:** hasil `I1_I7_RECONCILIATION` menyatakan `all_pass=true` dan `exact_recovery=true`. Terdapat 300 objek, 300 baris metadata, 300 recording ID unik, dan 300 URI objek unik.
- **Rincian invariant:** I1 tidak menemukan ID hilang; I2 tidak menemukan ID duplikat atau kosong; I3 tidak menemukan metadata yang berbeda dari ground truth; I4 tidak menemukan objek yatim; I5 tidak menemukan metadata tanpa objek; I6 memeriksa SHA-256 seluruh 300 WAV (1.056.240.000 byte) tanpa mismatch; I7 tidak menemukan baris metadata tambahan.
- **Durasi audit:** 56,598 detik. Audit I1–I7 ini membaca hasil B1/F0 setelah ingest; bukan pengujian fault/restart.
- **Bukti mentah:** `docs/evidence/e0-b1-f0-20261121.log` (2.409.190 byte), berisi keluaran reset, ingest, dan audit.
- **Status perbandingan E0:** B0/F0 dan B1/F0 sudah diulang dari keadaan bersih serta diaudit dengan I1–I7 yang sama. B2/F0 dan P1/F0 masih perlu dijalankan ulang dan diaudit dengan cara yang sama agar perbandingan empat treatment setara.

### Audit ulang B2/F0 untuk perbandingan E0 — 21 November 2026

- **Keadaan awal dan eksekusi:** `make reset` berakhir dengan `reset bersih`, lalu B2/F0 dijalankan dengan `RUN_ID=e0-b2-20261121`. Ingest selesai dengan kode keluar 0 dan 30 batch.
- **Audit setara:** hasil `I1_I7_RECONCILIATION` menyatakan `all_pass=true` dan `exact_recovery=true`. Terdapat 300 objek, 300 baris metadata, 300 recording ID unik, dan 300 URI objek unik.
- **Rincian invariant:** I1 tidak menemukan ID hilang; I2 tidak menemukan ID duplikat atau kosong; I3 tidak menemukan metadata yang berbeda dari ground truth; I4 tidak menemukan objek yatim; I5 tidak menemukan metadata tanpa objek; I6 memeriksa SHA-256 seluruh 300 WAV (1.056.240.000 byte) tanpa mismatch; I7 tidak menemukan baris metadata tambahan.
- **Durasi audit:** 55,708 detik. Setelah Spark menghentikan context dengan exit code 0, log mencatat `ERROR Inbox: Ignoring error` pada proses penutupan. Rekonsiliasi I1–I7 tetap selesai dan lulus; pesan penutupan ini dicatat agar bukti lengkap.
- **Bukti mentah:** `docs/evidence/e0-b2-f0-20261121.log` (13.163.147 byte), berisi keluaran reset, ingest, dan audit.
- **Status perbandingan E0:** B0/F0, B1/F0, dan B2/F0 sudah diulang dari keadaan bersih serta diaudit dengan I1–I7 yang sama. P1/F0 masih perlu dijalankan ulang dan diaudit agar perbandingan empat treatment setara.

### Audit ulang P1/F0 dan penutupan perbandingan E0 — 21 November 2026

- **Keadaan awal dan eksekusi:** `make reset` berakhir dengan `reset bersih`, lalu P1/F0 dijalankan dengan `RUN_ID=e0-p1-20261121`. Ingest selesai dengan kode keluar 0 dan 30 batch.
- **Audit setara:** hasil `I1_I7_RECONCILIATION` menyatakan `all_pass=true` dan `exact_recovery=true`. Terdapat 300 objek, 300 baris metadata, 300 recording ID unik, dan 300 URI objek unik.
- **Rincian invariant:** I1 tidak menemukan ID hilang; I2 tidak menemukan ID duplikat atau kosong; I3 tidak menemukan metadata yang berbeda dari ground truth; I4 tidak menemukan objek yatim; I5 tidak menemukan metadata tanpa objek; I6 memeriksa SHA-256 seluruh 300 WAV (1.056.240.000 byte) tanpa mismatch; I7 tidak menemukan baris metadata tambahan.
- **Durasi audit:** 55,501 detik. Audit ini membaca hasil P1/F0 setelah ingest; bukan pengujian fault/restart.
- **Bukti mentah:** `docs/evidence/e0-p1-f0-20261121.log` (13.162.599 byte), berisi keluaran reset, ingest, dan audit.
- **Status perbandingan E0:** B0/F0, B1/F0, B2/F0, dan P1/F0 kini sudah dijalankan ulang dari keadaan bersih serta diaudit dengan I1–I7 yang sama. Keempat hasil exact-recovery lulus. Hasil ini menutup perbandingan E0 pada F0; belum menyimpulkan hasil pengujian fault F1–F3.

### Persiapan F1 — keputusan posisi dan batas kegagalan — 22 November 2026

- **Prasyarat:** E0/F0 untuk B0, B1, B2, dan P1 telah lulus rekonsiliasi I1–I7 dengan keadaan awal bersih. Bagian ini menyiapkan F1; belum ada reset, kill, atau eksperimen F1 di Lightsail.
- **Definisi F1:** mengikuti keputusan D-39 pada panduan Minggu 2, F1 adalah SIGKILL pada proses driver sesudah PUT objek target terkonfirmasi dan sebelum baris metadata target di-commit. Pemulihan memakai `RUN_ID` yang sama, tanpa reset; driver pemulihan harus dijalankan dengan `FAULT_POINT=F0` agar tidak menyuntik kegagalan lagi.
- **Posisi yang dibekukan sebelum pilot:** `batch_id=14` (batch tengah dalam urutan 0–29), `record_index=5` (indeks 1-based dalam batch), sama untuk B0, B1, B2, dan P1. Batch tengah menghindari batas awal/akhir. Pada saat kill diharapkan 145 objek dan 144 baris metadata: seluruh 14 batch sebelumnya (140), empat rekaman pertama batch 14 (4), serta objek rekaman kelima (1). Rekaman kelima target belum memiliki metadata.
- **Hook driver:** `_process_event` menghitung posisi rekaman dan jumlah metadata yang sudah commit pada batch. Hanya setelah PUT baru terkonfirmasi pada target, driver menulis marker atomik `/signals/<RUN_ID>.kill` berisi target, titik kegagalan, batch, indeks, key, recording ID, jumlah commit terdahulu, dan waktu; lalu menunggu SIGKILL dari harness. F0 tidak membuat marker.
- **Bukti pra-pemulihan:** `src/reconciliation/snapshot_state.py` disiapkan sebagai pembaca saja. Ia menyimpan `objects.csv`, `metadata.csv`, dan `snapshot.json` di `/results/raw/<RUN_ID>/pra/`, lalu memeriksa objek target ada, metadata target belum ada, empat metadata sebelumnya ada, serta jumlah parsial sesuai rencana. Untuk B1/P1 ia juga memeriksa `offsets/14` ada dan `commits/14` belum ada. Salinan direktori checkpoint tetap diambil oleh langkah instrumen sebelum pemulihan.
- **Test lokal penyuntik:** seluruh suite lulus, 73 test, 0 gagal. Test memeriksa validasi rencana F0/F1, marker atomik, F0 tanpa marker, serta penolakan target tanpa PUT terkonfirmasi atau jumlah commit terdahulu yang keliru. `py_compile`, parse dua schema JSON, dan `git diff --check` juga lulus. Keluaran tersimpan di `docs/evidence/unittest-20261122-f1-local.txt`.
- **Batas bukti:** ini baru verifikasi lokal atas kode dan rencana. F1 belum dijalankan di Lightsail; sebelum pilot, perubahan harus tersedia di clone lab, environment harus cocok, lalu satu eksekusi harus membuktikan kill 137, snapshot pra-pemulihan, restart tanpa reset, dan rekonsiliasi.
- **Koreksi harness:** pilot pertama `w2-pilot-f1-B0-01` mencapai batas objek 5 batch 14, tetapi marker JSON tidak cocok dengan `kill_on_marker.sh` yang membaca baris `target=<nama kontainer>`. Harness mencatat `kill_error=target_not_found target=` dan kontainer masih menunggu; percobaan ini tidak dihitung sebagai bukti F1. Format marker diperbaiki menjadi kunci=nilai, dengan `target` pada baris pertama. Seluruh 73 test kembali lulus setelah perbaikan; bukti tersimpan di `docs/evidence/unittest-20261122-f1-keyvalue-local.txt`. Setelah kontainer lama dihentikan, hasil parsial harus di-reset sebelum run baru.

### Pilot F1 B0 pertama — 21 November 2026 UTC

- **Identitas:** `RUN_ID=w2-retry-f1-B0-01`, treatment B0, fault F1. Run sebelumnya dengan marker JSON dicatat sebagai kegagalan harness dan tidak dihitung; pilot ini memakai marker kunci=nilai yang dikenali instrumen.
- **Injeksi:** SIGKILL terkonfirmasi oleh `kill_on_marker.sh`; harness mencatat `kill_target=drv-w2-retry-f1-B0-01-a1`, `marker_fault_point=F1`, `marker_batch_id=14`, `marker_record_index=5`, dan `attempt1_exit_code=137`. Batas log menunjukkan PUT objek target selesai sebelum marker dan empat metadata pada batch tersebut sudah di-commit.
- **Snapshot pra-pemulihan:** pemeriksaan baca-saja lulus seluruhnya. Ada 145 objek dan 144 baris metadata; objek target `MAIN_5JAM_20260924_155400` ada, metadata target belum ada, dan empat metadata sebelumnya pada batch 14 ada. Checkpoint B0 tidak ditemukan di kontainer snapshot baru karena lokasinya ephemeral.
- **Pemulihan:** attempt 2 berjalan dengan RUN_ID sama dan FAULT_POINT=F0, tanpa reset. Replay selesai sampai audit internal F0, yang menolak 444 baris metadata (harapan F0 bersih: 300); kode keluar 1. Kegagalan pemeriksaan jumlah tersebut merupakan hasil B0/F1 yang harus dinilai lewat rekonsiliasi, bukan kegagalan injeksi.
- **Audit I1–I7:** `actual_object_count=300`, `actual_metadata_row_count=444`, dan 300 ID unik. I1 lulus (0 ID hilang); I2 gagal dengan 144 ID duplikat dan 144 baris berlebih (duplicate rate 0,48); I3, I4, I5 lulus; I6 lulus setelah meng-hash 300 objek / 1.056.240.000 byte; I7 lulus tanpa metadata tambahan. Hasil akhir `all_pass=false`, `exact_recovery=false`; durasi audit 56,792 detik.
- **Interpretasi:** checkpoint ephemeral menyebabkan replay dari awal. PUT berulang memakai key yang sama sehingga objek tetap 300, sedangkan append metadata B0 menghasilkan 144 baris duplikat. Hasil ini sesuai sifat at-least-once B0; belum menjadi kesimpulan matriks utama.
- **Bukti lokal:** `harness-w2-retry-f1-B0-01.log`, `w2-retry-f1-B0-01-attempt1.log`, `w2-retry-f1-B0-01-attempt2.log`, `snapshot-w2-retry-f1-B0-01.log`, dan `reconciliation-w2-retry-f1-B0-01.log` di `docs/evidence/`.
- **Status keterulangan:** run B0/F1 kedua dari reset bersih dicatat di bawah. Hasil injeksi, snapshot, jumlah objek, duplikasi metadata, dan seluruh invariant cocok dengan pilot pertama; keterulangan B0/F1 terkonfirmasi pada dua run.

### Ulangan B0/F1 kedua — 21 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-B0-02`. Harness mencatat `kill_target=drv-w2-retry-f1-B0-02-a1`, container ID `966c7191cf42`, `marker_fault_point=F1`, `marker_batch_id=14`, `marker_record_index=5`, serta exit code 137. Batas F1 tercapai sesudah PUT objek target dan sebelum metadata target di-commit.
- **Snapshot pra-pemulihan:** seluruh cek lulus: 145 objek, 144 baris metadata; objek target ada dan metadata target belum ada. Checkpoint B0 bersifat ephemeral dan tidak ada di kontainer snapshot.
- **Recovery:** dijalankan sekali dengan RUN_ID yang sama, tanpa reset. Log mencatat 30 `REPLAY_BATCH_COMPLETED`; pemeriksaan internal kemudian gagal dengan `expected 300, found 444`, sehingga attempt 2 keluar dengan kode 1. `INGESTION_FINISHED` tidak muncul karena exception audit terjadi lebih dahulu.
- **Audit I1–I7:** 300 objek, 444 baris metadata, 300 ID unik. I1 lulus tanpa ID hilang; I2 gagal dengan 144 ID duplikat dan 144 baris berlebih; I3–I7 lulus. I6 menghitung SHA-256 300 objek / 1.056.240.000 byte tanpa mismatch. `all_pass=false`, `exact_recovery=false`; durasi audit 62,198 detik.
- **Interpretasi dan keterulangan:** hasil ini sama dengan pilot B0/F1 pertama. Snapshot mengonfirmasi keadaan parsial yang direncanakan; recovery B0 mengulang seluruh 300 rekaman karena checkpoint ephemeral, menghasilkan 300 objek pada key yang sama dan menambahkan kembali 144 baris metadata yang sudah ada sebelum crash. Dua run sah kini menunjukkan hasil yang konsisten.
- **Bukti mentah:** `docs/evidence/harness-w2-retry-f1-B0-02.log`, `w2-retry-f1-B0-02-attempt1.log`, `w2-retry-f1-B0-02-attempt2.log`, `snapshot-w2-retry-f1-B0-02.log`, dan `reconciliation-w2-retry-f1-B0-02.log`. Harness pilot pertama dipertahankan sebagai `docs/evidence/harness-w2-retry-f1-B0-01.log`.
### Pilot F1 B1 pertama — 21 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-B1-01`. Harness mencatat `kill_target=drv-w2-retry-f1-B1-01-a1`, `marker_fault_point=F1`, batch 14, rekaman ke-5, dan exit code 137. Kegagalan terjadi setelah PUT objek target dan sebelum metadata target di-commit.
- **Snapshot pra-pemulihan:** seluruh cek lulus: 145 objek dan 144 baris metadata; objek target ada, metadata target belum ada. Checkpoint persistent B1 ada, offset batch 14 ada, dan commit batch 14 belum ada.
- **Recovery:** attempt 2 memakai RUN_ID yang sama tanpa reset. Replay mencapai batch 29, tetapi audit internal F0 menolak 304 baris metadata (ekspektasi 300); attempt 2 keluar dengan kode 1.
- **Audit I1–I7:** 300 objek, 304 baris metadata, dan 300 ID unik. I1 lulus tanpa ID hilang. I2 gagal karena 4 recording ID duplikat (`MAIN_5JAM_20260924_155000` sampai `MAIN_5JAM_20260924_155300`) dan 4 baris berlebih. I3–I7 lulus; I6 meng-hash 300 objek / 1.056.240.000 byte tanpa mismatch. `all_pass=false`, `exact_recovery=false`; durasi audit 53,281 detik.
- **Interpretasi:** checkpoint persistent mempertahankan posisi stream dan menghindari replay dari awal. Namun batch 14 belum memiliki commit saat driver mati, sehingga batch tersebut diproses ulang. Empat metadata yang sempat di-commit sebelum crash ditambahkan kembali; target dan rekaman berikutnya dicatat saat recovery. Hasil akhirnya 300 objek dan 4 baris metadata duplikat. Ini menunjukkan checkpoint saja belum memberi exactly-once pada efek samping metadata yang dilakukan sebelum commit batch.
- **Bukti mentah:** `docs/evidence/harness-w2-retry-f1-B1-01.log`, `w2-retry-f1-B1-01-attempt1.log`, `w2-retry-f1-B1-01-attempt2.log`, `snapshot-w2-retry-f1-B1-01.log`, dan `reconciliation-w2-retry-f1-B1-01.log`.
- **Status keterulangan:** hasil ulangan kedua dari reset bersih dicatat di bawah dan konsisten dengan pilot pertama. Dua run B1/F1 kini menunjukkan hasil yang sama; kesimpulan tetap terbatas pada skenario F1.
### Ulangan B1/F1 kedua — 21 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-B1-02`. Harness mencatat target `drv-w2-retry-f1-B1-02-a1`, fault F1, batch 14, rekaman ke-5, dan exit code 137.
- **Snapshot pra-pemulihan:** semua pemeriksaan lulus: 145 objek dan 144 baris metadata; objek target ada dan metadata target belum ada. Checkpoint persistent B1 ada, offset batch 14 ada, dan commit batch 14 belum ada.
- **Recovery:** dijalankan dengan RUN_ID sama tanpa reset. Replay mencapai batch 29; audit internal menolak 304 baris metadata (ekspektasi 300), sehingga attempt 2 keluar dengan kode 1.
- **Audit I1–I7:** 300 objek, 304 baris metadata, dan 300 ID unik. I1 serta I3–I7 lulus; I2 gagal dengan empat ID duplikat dan empat baris berlebih: `MAIN_5JAM_20260924_155000`, `..._155100`, `..._155200`, dan `..._155300`. I6 memeriksa SHA-256 seluruh 300 objek / 1.056.240.000 byte tanpa mismatch. Hasil `all_pass=false`, `exact_recovery=false`; durasi audit 53,812 detik.
- **Interpretasi:** hasil ini mengulang pilot B1/F1 pertama. Checkpoint persistent mencegah replay dari batch 0, tetapi batch 14 yang belum memiliki commit diproses ulang; empat metadata yang telah ditulis sebelum crash menjadi duplikat. Hasil dua run konsisten.
- **Bukti mentah:** `docs/evidence/harness-w2-retry-f1-B1-02.log`, `w2-retry-f1-B1-02-attempt1.log`, `w2-retry-f1-B1-02-attempt2.log`, `snapshot-w2-retry-f1-B1-02.log`, dan `reconciliation-w2-retry-f1-B1-02.log`.
### Pilot F1 B2 pertama — 22 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-B2-01`. F1 terjadi pada batch 14, rekaman ke-5, setelah PUT objek target dan sebelum metadata target di-commit. Harness mengonfirmasi target driver dan exit code 137.
- **Snapshot pra-pemulihan:** semua pemeriksaan lulus: 145 objek dan 144 baris metadata; objek target ada, metadata target belum ada. Checkpoint B2 ephemeral tidak bertahan di kontainer snapshot.
- **Recovery:** attempt 2 memakai RUN_ID yang sama tanpa reset. Replay menyelesaikan 30 batch; audit internal F0 melaporkan 300 objek, 300 baris metadata, 300 ID unik, dan exit code 0.
- **Audit I1–I7:** semua invariant lulus (`all_pass=true`, `exact_recovery=true`). Ada 300 objek dan 300 baris metadata; tidak ada ID hilang, duplikat, tambahan, objek yatim, metadata menggantung, atau mismatch metadata/byte. I6 menghitung SHA-256 seluruh 300 WAV (1.056.240.000 byte). Durasi audit 54,704 detik.
- **Interpretasi:** B2 kehilangan checkpoint ephemeral dan memutar ulang stream, tetapi idempotence guard mengenali objek serta metadata yang sudah sesuai sehingga hasil akhir tetap konsisten. Hasil pilot ini mendukung pemulihan tepat untuk B2/F1 pada run ini; satu run belum cukup untuk menyatakan keterulangan treatment.
- **Bukti mentah:** `docs/evidence/reset-before-w2-retry-f1-B2-01.log`, `harness-w2-retry-f1-B2-01.log`, `w2-retry-f1-B2-01-attempt1.log`, `w2-retry-f1-B2-01-attempt2.log`, `snapshot-w2-retry-f1-B2-01.log`, dan `reconciliation-w2-retry-f1-B2-01.log`.

### Ulangan B2/F1 kedua — 22 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-B2-02R`. Run pengganti dimulai setelah reset bersih. Harness mencatat F1 pada batch 14, rekaman ke-5 (`MAIN_5JAM_20260924_155400`), sesudah PUT objek dan sebelum metadata target di-commit. Driver mati dengan exit code 137 sesuai rencana.
- **Snapshot pra-pemulihan:** pemeriksaan baca-saja lulus: 145 objek, 144 baris metadata; objek target ada dan metadata target belum ada. Checkpoint ephemeral B2 tidak ditemukan.
- **Recovery:** attempt 2 memakai RUN_ID yang sama, tanpa reset. Log mencatat 30 batch selesai; `F0_RECONCILIATION` melaporkan 300 objek, 300 baris metadata, dan 300 ID unik. Attempt 2 berakhir dengan kode 0.
- **Audit I1–I7:** seluruh invariant lulus (`all_pass=true`, `exact_recovery=true`). Tidak ada ID hilang/duplikat/tambahan, metadata tidak cocok, objek yatim, atau metadata menggantung. I6 menghitung SHA-256 300 objek (1.056.240.000 byte) tanpa mismatch. Durasi audit 53,593 detik.
- **Urutan replay:** pemeriksa menyatakan `30 batch x 10 ID COCOK dengan batch_order_main.csv`.
- **Catatan run terdahulu:** `w2-retry-f1-B2-02` menghasilkan kondisi akhir yang lulus audit, tetapi log attempt 2 terputus sebelum batch 29 dan penanda selesai. Log dan audit terdahulu diarsipkan di VM sebagai run tidak lengkap; run pengganti ini dipakai sebagai ulangan kedua yang dapat diaudit.
- **Bukti mentah:** `docs/evidence/reset-before-w2-retry-f1-B2-02R.log`, `harness-w2-retry-f1-B2-02R.log`, `w2-retry-f1-B2-02R-attempt1.log`, `w2-retry-f1-B2-02R-attempt2.log`, `snapshot-w2-retry-f1-B2-02R.log`, `reconciliation-w2-retry-f1-B2-02R.log`, dan `verify-batches-w2-retry-f1-B2-02R.txt`.

### Pilot F1 P1 pertama — 22 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-P1-01`. F1 terjadi pada batch 14, rekaman ke-5 (`MAIN_5JAM_20260924_155400`), setelah PUT objek target dan sebelum metadata target di-commit. Harness mengonfirmasi exit code 137.
- **Snapshot pra-pemulihan:** pemeriksaan baca-saja lulus dengan 145 objek dan 144 baris metadata; objek target ada, metadata target belum ada. Checkpoint P1 persistent ditemukan: offset batch 14 ada, commit batch 14 belum ada.
- **Recovery:** attempt 2 memakai RUN_ID sama tanpa reset, berakhir dengan kode 0. Log internal mencatat 300 objek, 300 baris metadata, 300 ID unik, dan 30 batch selesai. Checkpoint setelah pemulihan berisi 30 commit bernomor.
- **Urutan replay:** log attempt 2 sendiri dimulai dari batch 14 karena checkpoint persistent. Setelah log attempt 1 dan 2 digabung, pemeriksa memverifikasi `30 batch x 10 ID COCOK dengan batch_order_main.csv`.
- **Audit I1–I7:** seluruh invariant lulus (`all_pass=true`, `exact_recovery=true`). Ada 300 objek dan 300 baris metadata; tidak ada yang hilang, duplikat, ekstra, yatim, menggantung, atau tidak cocok. I6 menghitung SHA-256 seluruh 300 WAV (1.056.240.000 byte) tanpa mismatch. Durasi audit 56,289 detik.
- **Bukti mentah:** `docs/evidence/reset-before-w2-retry-f1-P1-01.log`, `harness-w2-retry-f1-P1-01.log`, `w2-retry-f1-P1-01-attempt1.log`, `w2-retry-f1-P1-01-attempt2.log`, `snapshot-w2-retry-f1-P1-01.log`, `reconciliation-w2-retry-f1-P1-01.log`, `verify-batches-w2-retry-f1-P1-01.txt`, dan `checkpoint-w2-retry-f1-P1-01.txt`.

### Ulangan P1/F1 kedua — 22 November 2026 UTC

- **Identitas dan injeksi:** `RUN_ID=w2-retry-f1-P1-02`. Run dimulai setelah reset bersih. F1 terjadi pada batch 14, rekaman ke-5 (`MAIN_5JAM_20260924_155400`), sesudah PUT objek target dan sebelum metadata target di-commit; driver berakhir dengan exit code 137.
- **Snapshot pra-pemulihan:** snapshot baca-saja yang berhasil menunjukkan 145 objek dan 144 baris metadata; objek target ada, metadata target belum ada. Checkpoint persistent ditemukan dengan offset batch 14 ada dan commit batch 14 belum ada. Percobaan snapshot awal gagal karena direktori keluaran sudah ada; snapshot berhasil dijalankan ulang ke direktori baru dan digunakan sebagai bukti.
- **Recovery:** attempt 2 menggunakan RUN_ID sama tanpa reset, berakhir dengan kode 0. Log internal mencatat 300 objek, 300 baris metadata, 300 ID unik, dan 30 batch selesai. Checkpoint setelah recovery berisi 30 commit bernomor.
- **Urutan replay:** attempt 2 melanjutkan dari checkpoint. Setelah log attempt 1 dan 2 digabung, pemeriksa menyatakan `30 batch x 10 ID COCOK dengan batch_order_main.csv`.
- **Audit I1–I7:** seluruh invariant lulus (`all_pass=true`, `exact_recovery=true`). Ada 300 objek dan 300 baris metadata tanpa ID hilang, duplikat, ekstra, metadata tidak cocok, objek yatim, atau metadata menggantung. I6 menghitung SHA-256 300 WAV (1.056.240.000 byte) tanpa mismatch. Durasi audit 53,187 detik.
- **Bukti mentah:** `docs/evidence/reset-before-w2-retry-f1-P1-02.log`, `harness-w2-retry-f1-P1-02.log`, `w2-retry-f1-P1-02-attempt1.log`, `w2-retry-f1-P1-02-attempt2.log`, `snapshot-w2-retry-f1-P1-02-rerun.log`, `reconciliation-w2-retry-f1-P1-02.log`, `verify-batches-w2-retry-f1-P1-02.txt`, dan `checkpoint-w2-retry-f1-P1-02.txt`.
