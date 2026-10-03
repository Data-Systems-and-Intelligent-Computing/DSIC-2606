# Laporan Profiling Korpus Beku (Gate Minggu 1)
**Status:** Menunggu peninjauan berkas anomali 488 byte dan verifikasi log Spark.

| Parameter yang Dilaporkan | Corpus B (Utama - MAIN_5JAM) | Corpus A (Robustness - 3 Lokasi) |
| :--- | :--- | :--- |
| **Jumlah Berkas** | 301 | 322 |
| **Ukuran Total** | 1.056.240.488 byte (1.007,31 MiB) | 1.126.656.976 byte (1.074,46 MiB) |
| **Jumlah Perangkat** | 1 (`MAIN_5JAM`) | 3 (`KANTIN`, `EMBUNGD`, `KEBUNRAYA`) |
| **Rentang Timestamp (UTC)** | 2026-09-24 06:30:00 – 11:32:32<br>*(Durasi aktual: 5 jam 2 mnt 32 dtk)* | **Kantin:** 2026-09-23 03:00:00 – 05:01:45<br>**Embung D:** 2026-09-25 05:10:00 – 06:58:30<br>**Kebun Raya:** 2026-09-24 04:10:00 – 05:49:00 |
| **Distribusi Ukuran** | 300 $\times$ 3.520.800 byte<br>1 $\times$ 488 byte | 320 $\times$ 3.520.800 byte<br>2 $\times$ 488 byte |
| **Jumlah Micro-batch Spark** | **Belum Diverifikasi.**<br>*(Menunggu implementasi dan log eksekusi Spark aktual pada pipeline)* | **Belum Diverifikasi.**<br>*(Menunggu implementasi dan log eksekusi Spark aktual pada pipeline)* |
| **Catatan Temuan EDA** | 1 file (488 byte) & 1 jeda anomali (212 detik) di akhir sesi **sedang ditinjau** kesengajaannya sebelum dipertahankan. | 2 file (488 byte) & 2 jeda anomali di akhir sesi **sedang ditinjau** kesengajaannya sebelum dipertahankan. |C

### Bukti Pengujian Stabilitas Identitas & Zona Waktu (Unit Test)
* **Tanggal Eksekusi:** Oktober 2026
* **Status:** **LULUS (OK)**
* **Jumlah Tes Berjalan:** 2 tes (`test_manifest_identity_uri_dan_utc_konsisten`, `test_naive_timestamp_digagalkan`)
* **Waktu Eksekusi:** 0.113 detik
* **Kesimpulan:** Sistem secara otomatis menolak waktu yang ambigu (*naive timestamp*) dan mengonfirmasi bahwa seluruh `recording_id` serta `expected_object_uri` di keempat manifes konsisten secara absolut dengan aturan UTC.

### Bukti Pengujian Integritas Manifes (Unit Test)
* **Tanggal Eksekusi:** Oktober 2026
* **Status:** **LULUS (OK)** ($0.018$ detik)
* **Cakupan Tes:**
  * `test_recording_id_tidak_kosong_dan_unik`: Mengonfirmasi bahwa seluruh rekaman di keempat manifes memiliki identitas unik dan tidak ada duplikasi ID lintas korpus.
  * `test_sha256_tidak_kosong_dan_formatnya_valid`: Memastikan tidak ada nilai *hash* yang kosong dan seluruhnya sesuai standar format SHA-256 (64 karakter heksadesimal).
