# Rumusan Pertanyaan Penelitian — RQ v1

**Status: DRAFT — menunggu keputusan pembimbing D-03.**

Dokumen ini merangkum pertanyaan penelitian dan hipotesis untuk evaluasi
checkpointing dan idempotent ingestion pada pipeline AudioMoth. Versi ini
mengikuti rumusan pada bagian *Research Question* dan *Hipotesis* di `README.md`.
Rumusan belum ditetapkan sebagai versi final sampai keputusan D-03 diterima.

## Pertanyaan penelitian utama

**RQ1.** Bagaimana persistent checkpointing dan application-level idempotent
ingestion, secara sendiri-sendiri dan dalam kombinasi, memengaruhi *post-recovery
data correctness* pada pipeline ingestion AudioMoth ketika kegagalan terjadi di
antara penulisan objek WAV, commit metadata, dan commit checkpoint?

## Pertanyaan penelitian turunan

**RQ2.** Apakah strategi checkpoint-only (B1) mencegah keadaan duplikat atau
kehilangan data ketika kegagalan terjadi setelah efek samping eksternal tetapi
sebelum batch dianggap committed, dibandingkan baseline B0?

**RQ3.** Apakah strategi idempotence-only (B2) mempertahankan keadaan akhir yang
tepat ketika pipeline memutar ulang pekerjaan dari progres yang lebih awal, dan
berapa biaya pemrosesan ulangnya?

**RQ4.** Apakah kombinasi checkpoint dan idempotence (P1) mencapai correctness
yang setara atau lebih baik daripada B2 dengan jumlah data yang diproses ulang
lebih rendah?

**RQ5.** Pada setiap strategi, bagaimana titik kegagalan memengaruhi kemunculan
objek yatim (*orphan object*), metadata tanpa objek (*dangling metadata*),
record logis duplikat, atau ketidakcocokan checksum?

## Hipotesis kerja

Hipotesis berikut adalah dugaan yang akan diuji; hasil boleh menolaknya.

- **H1 — Checkpoint-only tidak selalu cukup.** Jika kegagalan terjadi sebelum
  checkpoint commit, B1 masih dapat mengulang efek samping yang sudah terjadi.
  Bila itu tidak teramati, mekanisme sink atau checkpoint pada implementasi yang
  diuji harus dijelaskan.
- **H2 — Idempotence menjaga keadaan akhir.** B2 diharapkan memperoleh *Exact
  Recovery Rate* tinggi meskipun cakupan replay lebih luas. Jika tidak, audit
  deterministic object key, checksum guard, metadata upsert, race lintas-sink,
  dan partial failure.
- **H3 — Kombinasi dapat menekan biaya pemulihan.** P1 diharapkan mencapai
  correctness setara atau lebih baik dari B2 dengan berkas atau byte yang
  diproses ulang lebih sedikit.
- **H4 — Posisi kegagalan memengaruhi jenis inkonsistensi.** Pola orphan,
  dangling, duplikasi, dan checksum mismatch diperkirakan berbeda menurut
  posisi kegagalan.

## Batas interpretasi

Penelitian mengukur correctness setelah pemulihan melalui kesesuaian objek WAV
dan metadata terhadap ground-truth manifest serta invarian I1–I7. Penelitian
tidak menganggap keberhasilan restart sebagai bukti correctness. Istilah
*exactly-once* tidak digunakan sebagai klaim kecuali kesetaraan keadaan end-to-end
terbukti pada seluruh failure point yang diuji. Hipotesis tidak dianggap benar
sebelum hasil eksperimen tersedia.

## Perbedaan dari rumusan di manuskrip saat ini

| Aspek | RQ v1 ini | `paper/manuscript.md` saat ini |
|---|---|---|
| Pertanyaan utama | Menyebut persistent checkpointing, application-level idempotence, dan urutan failure di antara PUT objek, commit metadata, serta commit checkpoint. | Menanyakan pengaruh checkpointing dan idempotent ingestion secara umum terhadap kehilangan, duplikasi, dan konsistensi objek-metadata. |
| Perbandingan treatment | Memisahkan B1, B2, dan P1 untuk mengisolasi efek checkpoint, idempotence, dan kombinasinya. | Subpertanyaan membahas treatment, tetapi tidak merumuskan secara eksplisit perbandingan biaya pemrosesan ulang P1 terhadap B2. |
| Failure point | Mengaitkan pertanyaan dengan tahapan efek samping dan commit yang diuji. | Menyebut F0–F3 pada subpertanyaan, tanpa menyatakan urutan commit di pertanyaan utama. |
| Hipotesis | H1–H4 ditulis sebagai hipotesis yang dapat ditolak. | Bagian yang ditampilkan berisi RQ dan sub-RQ; hipotesis kerja ada di README. |

Perbedaan ini dicatat untuk dibahas pada keputusan D-03. Dokumen manuskrip tidak
diubah dalam langkah ini.
