# Batas Publikasi (Delimitasi Penelitian)

Penelitian ini memiliki batasan ruang lingkup yang tegas sebagai berikut:

* **Tidak menganalisis isi/konten akustik:** Berkas `.WAV` hasil rekaman AudioMoth diperlakukan secara murni sebagai objek biner yang tidak dapat diubah (*immutable*). Tidak ada ekstraksi fitur suara, klasifikasi spesies, maupun analisis ekologis.
* **Tidak mengklaim semantik *exactly-once*:** Istilah teknis ini dilarang dan tidak akan digunakan dalam laporan akhir, kecuali kesetaraan keadaan ganda benar-benar terbukti secara *end-to-end* secara matematis.
* **Tidak berfokus pada optimasi kinerja:** Fokus pengujian murni dititikberatkan pada korektnes (kebenaran) data pasca-pemulihan, bukan pada seberapa cepat waktu pemulihannya.
* **Tidak menguji titik kegagalan perangkat keras:** Tidak ada pengujian untuk kegagalan fisik (misal: baterai habis, kerusakan *SD Card*). Pengujian difokuskan pada kegagalan *pipeline* perangkat lunak (titik kegagalan F1 hingga F3).
* **Skala eksekusi terkendali:** Tidak melakukan pengujian *production/real-time* berskala besar di luar parameter 128 eksekusi independen yang telah dirancang pada dokumen arsitektur.