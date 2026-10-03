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