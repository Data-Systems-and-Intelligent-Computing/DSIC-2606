# Rumusan Pertanyaan Penelitian — RQ v1

**Status: berlaku sebagai RQ penelitian (D-03, 20 November 2026; penutupan Gate Minggu 1 bersyarat D-41).**

Dokumen ini merangkum pertanyaan penelitian dan hipotesis untuk evaluasi
checkpointing dan idempotent ingestion pada pipeline AudioMoth. Versi ini
mengikuti rumusan pada bagian *Research Question* dan *Hipotesis* di `README.md`.
Rumusan ini berlaku sesuai keputusan D-03. Aturan keputusan statistik tetap mengikuti pembekuan pada Hari 17.

## Pertanyaan penelitian utama

**RQ1.** Bagaimana persistent checkpointing dan application-level idempotent
ingestion, secara sendiri-sendiri dan dalam kombinasi, memengaruhi *post-recovery
data correctness* pada pipeline ingestion AudioMoth ketika kegagalan terjadi di
antara penulisan objek WAV, commit metadata, dan commit checkpoint?

## Pertanyaan penelitian turunan

**RQ2.** Apakah checkpoint-only mencegah state duplikat/hilang ketika kegagalan
terjadi setelah efek samping eksternal tetapi sebelum batch dianggap committed?

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
*exactly-once* tidak digunakan sebagai klaim hasil; kesimpulan dibatasi pada
*post-recovery correctness* dan *exact recovery* di failure point yang diuji.
Hipotesis tidak dianggap benar sebelum hasil eksperimen tersedia.

## Penyelarasan dengan manuskrip

Sebelum keputusan D-03, rumusan di manuskrip berbeda dari README: terutama,
RQ3–RQ4 belum menanyakan biaya pemrosesan ulang. Sesuai D-41, bagian RQ di
`paper/manuscript.md` kini diselaraskan dengan RQ1–RQ5 di atas. Hipotesis H1–H4
mengikuti README dan tetap dapat ditolak berdasarkan hasil.
