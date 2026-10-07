# Draf Spesifikasi Lingkungan Eksperimen Fase 2

- **Status:** DRAFT — menunggu tinjauan dan nilai standar laboratorium
- **Tujuan:** Menyepakati spesifikasi layanan yang akan dideploy oleh laboratorium melalui OpenTofu sebelum uji Fase 2.
- **Batas dokumen:** Ini dokumen rancangan untuk ditinjau, bukan konfigurasi OpenTofu/Compose siap deploy dan bukan catatan lingkungan yang sudah dibekukan.

## 1. Prinsip yang harus dipertahankan

1. Semua perlakuan eksperimen memakai versi layanan, batas sumber daya, jaringan, dan susunan layanan yang sama.
2. Perbandingan B0 dan B1 hanya mengubah konfigurasi lokasi checkpoint yang ditetapkan protokol. B0 memakai lokasi sementara yang hilang saat kontainer terkait dihapus; B1 memakai lokasi persisten yang bertahan saat proses Spark dimulai ulang.
3. Checkpoint tidak disimpan di MinIO.
4. Volume korpus dipasang read-only agar data acuan tidak berubah selama eksperimen. Kode eksperimen juga dipasang read-only bila sesuai instrumen lab.
5. Nilai CPU/RAM per layanan, versi image, dan digest harus berasal dari standar/instrumen laboratorium atau hasil runtime yang disetujui. Nilai tersebut tidak diturunkan dari kapasitas total VM.

## 2. Komponen dan nilai yang perlu dikonfirmasi

| Komponen/hal | Rancangan saat ini | Status |
| --- | --- | --- |
| Pemroses streaming | Apache Spark; detail driver, executor, dan konfigurasi final mengikuti instrumen lab | Versi, image, digest, dan bentuk layanan menunggu standar lab |
| Object storage | MinIO sebagai sink S3 kompatibel | Versi, image, digest, bucket/prefix, dan kebijakan persistensi menunggu konfirmasi |
| Katalog tabel | Apache Iceberg dengan katalog berbasis database sesuai protokol | Implementasi katalog, layanan database, versi, image, dan digest menunggu konfirmasi |
| Layanan audit/query tambahan | Belum ditetapkan sebagai bagian eksperimen | Jangan dimasukkan kecuali disetujui lab |
| Batas CPU dan RAM | Satu batas CPU dan memori untuk setiap layanan | **Menunggu nilai standar lab** |
| Checkpoint B0 | Penyimpanan sementara di lingkungan kontainer Spark; hilang saat kontainer terkait dihapus | Path dan mekanisme reset menunggu instrumen lab |
| Checkpoint B1 | Penyimpanan persisten di luar MinIO | Path/volume persisten dan izin tulis menunggu konfirmasi |
| Korpus | Mount `/data/corpus/main` pada VM, read-only untuk proses eksperimen | Cara mount ke layanan mengikuti Compose/instrumen lab |
| Kode eksperimen | Mount kode yang dibutuhkan dengan akses read-only bila didukung instrumen | Path final menunggu instrumen lab |
| Lingkungan host | VM lab `dsic-lab-01`; spesifikasi host yang tercatat di manifest adalah konteks host, bukan batas layanan | Pertahankan nilai host terpisah dari batas per layanan |

## 3. Nilai yang belum boleh dianggap final

Hal-hal berikut belum ditentukan dalam draf ini dan perlu diisi setelah standar lab atau instrumen final diterima:

- nama layanan dan susunan kontainer yang benar-benar dipakai;
- tag versi dan digest image untuk setiap layanan;
- batas CPU dan RAM tiap layanan;
- path serta jenis volume untuk checkpoint persisten B1;
- lokasi sementara checkpoint B0 dan cara reset yang resmi;
- volume data MinIO dan metadata/catalog database, termasuk apakah datanya persisten;
- nama bucket/prefix dan jaringan/port yang diperlukan;
- health check, skrip preflight/reset, ambang multipart, dan instrumen pencatat runtime.

## 4. Bukti runtime yang akan dibekukan setelah deployment

Setelah instrumen berjalan dan nilainya diverifikasi, catat nilai aktual—bukan nilai rancangan—di berkas kunci lingkungan dan manifest proyek:

- versi perangkat lunak;
- image reference dan digest yang benar-benar berjalan;
- batas CPU/RAM yang diterapkan pada setiap layanan;
- konfigurasi mount dan checkpoint yang efektif;
- hasil pemeriksaan layanan sehat serta identitas lingkungan.

Manifest runtime baru berstatus **frozen** setelah nilai aktual tersedia dan diverifikasi. Draf ini sendiri tidak membekukan versi atau resource.

## 5. Pertanyaan tinjauan untuk standar laboratorium

Mohon konfirmasi sebelum spesifikasi ini dijadikan input deployment:

1. Apakah format yang diperlukan berupa dokumen kebutuhan seperti ini, file Compose, variabel input OpenTofu, atau kombinasi tertentu?
2. Layanan apa saja yang wajib dijalankan untuk eksperimen, termasuk layanan database katalog Iceberg?
3. Apa image, tag versi, dan digest standar untuk masing-masing layanan?
4. Berapa batas CPU dan RAM per layanan yang harus digunakan pada VM lab?
5. Di mana lokasi volume persisten B1, lokasi sementara B0, dan bagaimana aturan reset keduanya?
6. Volume mana yang wajib read-only, dan bagaimana kebijakan persistensi data MinIO serta database katalog?
7. Instrumen final mana yang harus dijalankan untuk health check, reset/preflight, dan pencatatan kunci runtime?

## 6. Langkah berikutnya

Tinjau draf ini bersama pembimbing/laboratorium. Setelah nilai standar dan bentuk input deployment dikonfirmasi, perbarui spesifikasi. Jangan mengisi nilai yang belum diketahui dengan perkiraan. Setelah deployment, cocokkan spesifikasi dengan nilai runtime sebelum memperbarui manifest final.
