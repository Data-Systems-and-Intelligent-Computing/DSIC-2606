# Batas Publikasi (Delimitasi Penelitian)

**Status: berlaku bersama RQ v1 sesuai D-03 (20 November 2026); penutupan Gate Minggu 1 bersyarat D-41.**

Penelitian ini memiliki batasan ruang lingkup yang tegas sebagai berikut:

* **Tidak menganalisis isi/konten akustik:** Berkas `.WAV` hasil rekaman AudioMoth diperlakukan secara murni sebagai objek biner yang tidak dapat diubah (*immutable*). Tidak ada ekstraksi fitur suara, klasifikasi spesies, maupun analisis ekologis.
* **Tidak mengklaim semantik *exactly-once*:** penelitian membatasi klaim pada *post-recovery correctness* dan *exact recovery* yang diuji terhadap objek dan metadata. Keberhasilan pada failure point yang diuji tidak digeneralisasi menjadi jaminan *exactly-once* end-to-end.
* **Tidak berfokus pada optimasi kinerja:** Fokus pengujian murni dititikberatkan pada korektnes (kebenaran) data pasca-pemulihan, bukan pada seberapa cepat waktu pemulihannya.
* **Tidak menguji titik kegagalan perangkat keras:** Tidak ada pengujian untuk kegagalan fisik (misal: baterai habis, kerusakan *SD Card*). Pengujian difokuskan pada kegagalan *pipeline* perangkat lunak (titik kegagalan F1 hingga F3).
* **Skala eksekusi terkendali:** Tidak melakukan pengujian *production/real-time* berskala besar di luar parameter 128 eksekusi independen yang telah dirancang pada dokumen arsitektur.

## Klaim yang tidak dibuat

Penelitian ini tidak menyimpulkan bahwa:

1. Spark menjamin semantik *exactly-once* end-to-end.
2. Checkpoint mencegah semua duplikasi efek samping eksternal.
3. Idempotence dapat menggantikan checkpoint.
4. MinIO dan Iceberg bertransaksi secara atomik sebagai satu sistem lintas dua state.
5. AudioMoth memerlukan algoritma pemulihan khusus.
6. Penelitian ini adalah pipeline bioakustik toleran kegagalan yang pertama.

Klaim harus dibatasi pada konfigurasi, failure point, korpus, dan bukti yang
benar-benar diuji. Bahasa hasil yang digunakan adalah *post-recovery correctness*
dan *exact recovery*; istilah *exactly-once* tidak dipakai sebagai klaim hasil.

## Cakupan kerja untuk Gate Minggu 1

Gate Minggu 1 membekukan korpus Main yang terdiri dari 300 WAV dan 30 batch
berisi 10 recording ID, memeriksa identitas dan metadata terhadap manifest, serta
membuktikan kesiapan dan perilaku awal B0/B1 pada F0. Gate ini menyiapkan dasar
eksperimen pemulihan; gate ini sendiri belum menguji hipotesis F1–F3 atau
menetapkan hasil akhir tentang recovery.
