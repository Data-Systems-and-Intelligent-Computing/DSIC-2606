## 1. Rumusan Masalah (Research Question)

**Pertanyaan Penelitian Utama (RQ1):**
Bagaimana *persistent checkpointing* dan *application-level idempotent ingestion*, secara sendiri-sendiri dan dalam kombinasi, memengaruhi *post-recovery data correctness* ketika kegagalan terjadi di antara penulisan objek WAV, *metadata commit*, dan *checkpoint commit*?

**Pertanyaan Penelitian Turunan:**
**RQ2.** Apakah *checkpoint-only* mencegah state duplikat atau hilang ketika kegagalan terjadi setelah efek samping eksternal tetapi sebelum batch dianggap *committed*?
**RQ3.** Apakah *idempotence-only* mempertahankan *exact final state* meskipun replay dimulai dari progres yang lebih awal, dan berapa biaya pemrosesan ulangnya?
**RQ4.** Apakah kombinasi *checkpoint* dan *idempotence* memberi *exact recovery* dengan pemrosesan ulang lebih rendah dibanding *idempotence-only*?
**RQ5.** Titik kegagalan mana yang paling sering menghasilkan objek *orphan*, metadata *dangling*, duplikat logis, atau *checksum mismatch* pada setiap strategi?

Rumusan RQ dan hipotesis mengikuti bagian *Research Question* dan *Hipotesis*
di `README.md`, sesuai keputusan pembimbing D-03. Aturan keputusan statistik
akan dibekukan sebelum matriks utama dijalankan.
