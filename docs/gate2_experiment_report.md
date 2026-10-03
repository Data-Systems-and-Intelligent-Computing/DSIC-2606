### Bukti Isolasi Variabel Eksperimen B0 dan B1 (Unit Test)
* **Tanggal Eksekusi:** Oktober 2026
* **Status:** **LULUS (OK)** (0.006 detik)
* **Bukti Integritas Eksperimen:**
  1. `test_b0_and_b1_differ_only_by_checkpoint_location`: Berhasil memvalidasi bahwa selisih konfigurasi antara perlakuan B0 dan B1 benar-benar **hanya satu kunci** (`checkpoint_location`).
  2. `test_b0_resolves_to_no_checkpoint`: Memastikan B0 berjalan murni sebagai *baseline* (tanpa checkpoint persisten).
  3. `test_b1_requires_a_persistent_root_and_resolves_per_run`: Memastikan B1 menggunakan *checkpoint* yang terisolasi secara aman untuk setiap ID pengujian.
  4. `test_idempotence_is_off_for_both_treatments`: Idempotence sengaja dimatikan untuk mengukur efek pemulihan murni bawaan sistem.