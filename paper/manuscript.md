## 1. Rumusan Masalah (Research Question)

**Pertanyaan Penelitian Utama (RQ):**
Bagaimana *checkpointing* dan *idempotent ingestion* memengaruhi kebenaran data pasca-pemulihan pada *pipeline ingestion* AudioMoth berbasis objek, ditinjau dari kehilangan rekaman, duplikasi, dan konsistensi antara objek audio dan metadata?

**Pertanyaan Turunan (Sub-RQ):**
1. Sejauh mana strategi *retry* sederhana (B0) mampu menjaga kelengkapan dan keunikan data pasca-kegagalan?
2. Bagaimana *checkpointing* (B1) memengaruhi konsistensi referensial dan tingkat duplikasi dibanding strategi B0?
3. Bagaimana *idempotent ingestion* (B2) memengaruhi risiko objek yatim (*orphan*) dan metadata gaib (*dangling*)?
4. Apakah kombinasi *checkpointing* dan *idempotence* (P1) menghasilkan *Exact Recovery Rate* tertinggi dibandingkan ketiga strategi lainnya?
5. Bagaimana titik kegagalan (F0-F3) memengaruhi jenis pelanggaran invarian (I1-I7) yang muncul pada tiap strategi?