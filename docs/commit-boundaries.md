# Batas commit pada alur ingest B0/B1

## Satu rekaman

1. Driver membaca satu event JSON dari landing Spark. Event berisi 10 `recording_id` dan harus cocok tepat dengan batch yang sama di `batch_order_main.csv`.
2. Untuk setiap ID sesuai urutan event, driver mencari baris manifest dan berkas WAV pada mount read-only `/data/raw`.
3. Kode memeriksa ukuran dan SHA-256 WAV terhadap manifest.
4. Pipeline mengirim WAV ke bucket/key dari `expected_object_uri` melalui MinIO S3 API. PUT dianggap selesai setelah permintaan `upload_file` berhasil dan `HEAD` mengonfirmasi ukuran serta metadata SHA-256 yang sama. Bukti dicatat sebagai `OBJECT_PUT_COMPLETED`.
5. Setelah PUT satu WAV dikonfirmasi, pipeline menambahkan satu baris ke tabel Iceberg `lab.main.recordings`. Batas commit metadata adalah saat `.writeTo(...).append()` berhasil kembali. Bukti dicatat sebagai `ICEBERG_COMMIT_COMPLETED`.
6. Setelah sepuluh rekaman dalam event selesai, Spark callback kembali. Barulah Spark mencatat commit micro-batch pada checkpoint. Feeder baru kemudian menerbitkan event berikutnya.

Tabel `lab.main.recordings` adalah keputusan implementasi Fase 3; tabel `lab.smoke.t` milik smoke test instrumen dan tidak dipakai sebagai tabel penelitian. Reset lab harus dijalankan sesuai prosedur sebelum F0 supaya tabel dan bucket mulai kosong.

## Arti kegagalan untuk baseline at-least-once

B0 dan B1 sama-sama tidak memeriksa apakah objek atau baris metadata sudah pernah ditulis. Jika driver mati setelah PUT tetapi sebelum commit Iceberg, percobaan ulang dapat PUT ulang key yang sama. Jika mati setelah commit Iceberg tetapi sebelum Spark menyimpan commit micro-batch, percobaan ulang dapat menambahkan baris metadata duplikat. PUT ke key yang sama menimpa objek dengan identitas yang sama, sedangkan append Iceberg dapat menambah baris lagi. Perbedaan daya tahan checkpoint menentukan progres stream yang pulih; lokasi checkpoint adalah satu-satunya perbedaan treatment.

## Batas bukti saat ini

Implementasi dan test lokal memeriksa penyusunan URI, validasi sumber manifest, urutan event, dan pilihan konfigurasi. Belum ada bukti Spark F0 sampai pipeline dijalankan pada stack Lightsail. Label `OBJECT_PUT_COMPLETED`, `ICEBERG_COMMIT_COMPLETED`, jumlah 300/300, urutan micro-batch, serta perbedaan hasil setelah restart harus dibuktikan dari log eksekusi VM.
