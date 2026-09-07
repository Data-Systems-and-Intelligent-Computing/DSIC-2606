# DSIC-2606 — Checkpointing, Idempotence, and Post-Recovery Correctness in AudioMoth Ingestion

Repository penelitian **DSIC-2606**.

Judul penelitian yang direkomendasikan:

> **Post-Recovery Data Correctness under Checkpointing and Idempotent Ingestion in an Object-Based AudioMoth Pipeline**

Alternatif lebih systems-oriented:

> **Checkpointing, Idempotence, and Exact Recovery in Object–Metadata Ingestion Pipelines**

Judul *When Checkpointing Is Not Enough* hanya dipakai bila hasil benar-benar menunjukkan residual inconsistency pada checkpoint-only treatment.

---

## Keputusan Pembimbing

Penelitian diteruskan, tetapi objek ilmiahnya harus tetap:

> **post-recovery data correctness pada object-based ingestion pipeline setelah controlled failure.**

AudioMoth hanya menjadi testbed berupa frozen corpus WAV. WAV diperlakukan sebagai **immutable binary object**. Tidak ada klasifikasi spesies, feature extraction, MFCC, embedding, atau analisis ekologis.

Eksperimen tidak boleh hanya membuktikan bahwa pipeline hidup kembali. Setiap run harus selesai dengan rekonsiliasi terhadap **frozen ground-truth manifest**.

Kontribusi ilmiah bukan penggunaan:
- AudioMoth;
- WAV;
- MinIO;
- Apache Iceberg;
- Spark Structured Streaming;
- SHA-256;
- checkpointing;
- idempotence;
- at-least-once.

Kontribusi yang diuji adalah:

> **controlled factorial evaluation terhadap persistent checkpointing dan application-level idempotence pada dual-state ingestion yang harus menjaga konsistensi canonical WAV object dan metadata record di bawah staged failures.**

---

## Kalimat Jangkar Penelitian

> Penelitian ini mengevaluasi secara factorial pengaruh persistent checkpointing dan application-level idempotence terhadap post-recovery correctness pada ingestion pipeline berbasis objek, dengan staged failure di antara object write, metadata commit, dan checkpoint commit, lalu memverifikasi exact state equivalence antara object dan metadata terhadap frozen ground-truth manifest.

---

## Publication Boundary

Penelitian ini tidak mengklaim:
- Spark menjamin exactly-once end-to-end;
- checkpoint mencegah semua external-side-effect duplicate;
- idempotence menggantikan checkpoint;
- MinIO + Iceberg transactional secara atomik lintas dua state;
- AudioMoth memerlukan algoritma recovery khusus;
- penelitian ini adalah fault-tolerant bioacoustic pipeline pertama.

Bahasa klaim yang aman:

> **checkpointing membatasi replay dari progress yang telah committed, sedangkan idempotence membatasi side effect dari repeated execution. Nilai kombinasi keduanya diuji melalui exact equivalence terhadap frozen object–metadata ground truth.**

Gunakan istilah:

```text
exact recovery
post-recovery correctness
```

Jangan menggunakan `exactly-once` sebelum dual-state equivalence benar-benar terbukti pada seluruh failure point yang diuji.

---

## Research Question

### RQ Utama

**RQ1. Bagaimana persistent checkpointing dan application-level idempotent ingestion, secara sendiri-sendiri dan dalam kombinasi, memengaruhi post-recovery data correctness pada pipeline ingestion AudioMoth ketika kegagalan terjadi di antara penulisan WAV object, metadata commit, dan checkpoint commit?**

### Sub-RQ

**RQ2.** Apakah checkpoint-only mencegah duplicate/missing state ketika failure terjadi setelah external side effect tetapi sebelum batch dianggap committed?

**RQ3.** Apakah idempotence-only mempertahankan exact final state meskipun pipeline harus replay dari progress yang lebih awal, dan berapa biaya reprocessing-nya?

**RQ4.** Apakah checkpoint + idempotence memberi exact recovery dengan reprocessing yang lebih rendah dibanding idempotence-only?

**RQ5.** Failure point mana yang paling sering menghasilkan orphan object, dangling metadata, duplicate logical record, atau checksum inconsistency pada setiap strategi?

---

## Hipotesis

### H1 — Checkpoint-Only Tidak Cukup

Pada failure sebelum checkpoint commit, B1 masih dapat menghasilkan duplicate/partial side effects.

Jika tidak terjadi, mekanisme sink/checkpoint pada implementation yang diuji harus dijelaskan; jangan memaksa hasil.

### H2 — Idempotence Menjaga Final State

B2 diharapkan memiliki Exact Recovery Rate tinggi meskipun replay lebih luas.

Jika gagal, audit:
- deterministic key;
- checksum guard;
- metadata upsert;
- cross-state race;
- partial failure.

### H3 — Kombinasi Paling Efisien

P1 diharapkan mencapai correctness setara atau lebih baik dari B2 dengan reprocessed files/bytes lebih rendah.

### H4 — Failure Point Matters

Pola orphan, dangling, duplicate, dan checksum mismatch diperkirakan berbeda menurut posisi failure.

Semua hipotesis boleh ditolak.

---

## Dataset

Gunakan:

```text
Frozen AudioMoth WAV corpus
```

Isi audio tidak dianalisis secara bioakustik. File diperlakukan sebagai immutable binary object.

Gunakan seluruh corpus bila nyaman direplay. Jika terlalu besar, freeze subset kronologis/berdasarkan device yang menghasilkan minimal **10–20 micro-batches**.

Laporkan angka nyata:
- jumlah file;
- total GB;
- jumlah device;
- rentang waktu rekaman;
- jumlah micro-batch;
- distribusi ukuran file.

---

## Ground-Truth Manifest

Setiap recording wajib memiliki:

```text
recording_id
device_id
start_time
source_path
file_size_bytes
sha256
expected_object_uri
expected_metadata
```

### recording_id

Stable logical identity. Tidak boleh berubah antar retry, run, treatment, atau failure point.

### sha256

Primary byte-level integrity check. Hash source dihitung sebelum main experiment.

### expected_object_uri

Canonical target object path.

### expected_metadata

Metadata yang harus persis atau semantically equivalent setelah recovery.

---

## Unit Analisis

Unit logical data:

```text
one recording_id
```

dengan dua state:

```text
1 canonical WAV object
+
1 metadata record
```

Unit statistik independen:

```text
one failure run
```

Bukan setiap file di dalam satu run.

---

## Arsitektur Eksperimen

```text
Frozen AudioMoth WAV Corpus
        ↓
Ground-Truth Manifest
recording_id | size | SHA-256
expected object | expected metadata
        ↓
Replay Manifest / Landing Events
        ↓
Spark Structured Streaming
micro-batch
        ↓
checkpoint OFF / persistent ON
        ↓
        ├────────────→ MinIO
        │              canonical WAV objects
        │
        └────────────→ Iceberg
                       metadata / ingestion ledger
        ↓
Controlled Failure
F0 | F1 | F2 | F3
        ↓
Retry / Restart
        ↓
Reconciliation Auditor
        ↓
I1–I7 correctness invariants
        ↓
Exact Recovery Rate
+
error taxonomy
+
reprocessing cost
```

---

## Tools Penelitian

### Spark Structured Streaming

Peran:
- micro-batch;
- task retry;
- persistent checkpoint;
- restart/replay substrate.

### MinIO

Peran:
- canonical WAV object sink;
- object existence audit;
- size/checksum audit.

### Apache Iceberg

Peran:
- metadata table;
- optional ingestion ledger;
- MERGE/upsert pada idempotent treatment;
- commit/snapshot audit.

### Python

Peran:
- manifest;
- SHA-256;
- fault injection;
- reconciliation;
- statistics;
- plots.

### Docker Compose

Peran:
- reproducible environment;
- deterministic process/container restart;
- fixed resource caps.

### Trino

Opsional untuk independent final-state query audit. Bukan komponen utama eksperimen.

---

## Factorial Treatment Design

Eksperimen utama adalah **2 × 2 factorial design**:

```text
checkpoint OFF/ON
×
idempotence OFF/ON
```

### B0 — No Checkpoint, No Idempotence

```text
checkpoint = OFF
idempotence = OFF
```

Naive but realistic at-least-once retry/restart. Jangan membuat baseline sengaja buruk.

### B1 — Checkpoint-Only

```text
checkpoint = ON
idempotence = OFF
```

Progress durable, external writes tetap non-idempotent.

### B2 — Idempotence-Only

```text
checkpoint = OFF
idempotence = ON
```

Replay dapat luas, tetapi repeated execution harus converge ke state logis yang sama.

### P1 — Checkpoint + Idempotence

```text
checkpoint = ON
idempotence = ON
```

Proposed treatment.

---

## Application-Level Idempotence

Treatment idempotent wajib memakai:

### Stable recording_id

Sama untuk seluruh replay.

### Deterministic Canonical Object Key

Contoh:

```text
device/date/recording_id.wav
```

Bukan random `run_id` atau UUID per retry.

### Object Guard

Sebelum dianggap berhasil:
- cek existence;
- cek size;
- cek checksum.

Repeated write dengan bytes identik tidak membuat logical duplicate.

Jika recording_id sama tetapi checksum berbeda:

```text
CONFLICT
```

bukan overwrite diam-diam.

### Metadata Upsert

Gunakan:
- MERGE;
- upsert;
- uniqueness pada `recording_id`.

### Ingestion Ledger Opsional

Field minimum:

```text
batch_id
recording_id
attempt_id
object_status
metadata_status
commit_timestamp
```

---

## Checkpoint Semantics

### Persistent ON

Checkpoint disimpan pada durable location yang tidak dihapus saat driver restart.

### OFF

Progress state tidak persistent; restart dapat memicu replay lebih luas.

Checkpoint bukan idempotence. Side effect dapat sudah terjadi sebelum batch/checkpoint commit.

---

## Failure Model

Failure injection harus deterministik melalui `fault_plan`.

Setiap run mencatat:
- batch_id;
- record index;
- stage;
- process/container target;
- failure mode;
- timestamp/trigger.

---

## F0 — No Failure Control

Mengukur correctness dan overhead tanpa failure.

Semua B0/B1/B2/P1 harus exact pada F0.

Jika F0 salah:

```text
STOP MAIN EXPERIMENT
```

---

## F1 — After Object PUT, Before Metadata Commit

Class:

```text
worker/task failure
```

Boundary:

```text
object PUT
   ↓
FAIL
   ↓
metadata belum committed
```

Mengukur:
- object-side idempotence;
- orphan object;
- duplicate object representation;
- retry side effects.

---

## F2 — After Metadata Commit, Before Checkpoint Commit

Class:

```text
pipeline/driver restart
```

Boundary:

```text
object PUT
   ↓
metadata commit
   ↓
FAIL
   ↓
checkpoint belum durable
```

Ini failure point paling penting untuk mengidentifikasi efek checkpoint.

---

## F3 — After Checkpoint Commit

Class:

```text
pipeline/driver restart control
```

Boundary:

```text
object PUT
   ↓
metadata commit
   ↓
checkpoint commit
   ↓
FAIL
```

Checkpoint-enabled treatment seharusnya tidak mengulang committed work secara material.

---

## Mengapa F1 Saja Tidak Cukup?

F1 terutama menguji retry + sink idempotence. Persistent checkpoint bisa tampak tidak berpengaruh.

Karena itu F2 dan F3 wajib ada.

---

## Correctness Invariants

Final state `S` dinyatakan exactly recovered terhadap ground truth `G` hanya jika semua invariant terpenuhi.

### I1 — Completeness

Setiap recording_id di G memiliki canonical object dan metadata row.

### I2 — Uniqueness

Tidak ada lebih dari satu logical metadata record atau active object representation per recording_id.

### I3 — Referential Consistency

`metadata.object_uri` menunjuk object yang benar-benar ada.

### I4 — No Orphan

Tidak ada WAV object hasil ingestion tanpa metadata canonical.

### I5 — No Dangling Metadata

Tidak ada metadata yang menunjuk object yang tidak ada.

### I6 — Byte Integrity

File size dan SHA-256 sama dengan frozen source manifest.

### I7 — No Extras

Tidak ada recording_id final yang tidak berasal dari ground-truth replay set.

---

## Exact Recovery Rate

```text
Exact Recovery Rate
=
run yang memenuhi I1–I7
/
seluruh independent run
```

Ini primary endpoint lebih kuat daripada sekadar rata-rata jumlah error.

---

## Primary Correctness Metrics

- missing recording count/rate;
- duplicate logical recording count/rate;
- orphan object count/rate;
- dangling metadata count/rate;
- checksum mismatch count/rate;
- Exact Recovery Rate;
- total invariant violations;
- state-divergence taxonomy.

Correctness selalu primer.

---

## Secondary Recovery-Cost Metrics

- reprocessed recording count;
- reprocessed bytes;
- recovery time;
- total ingestion completion time;
- failed/retried task count;
- attempt count;
- checkpoint write/storage overhead;
- metadata/object operations bila observable.

Recovery time tidak boleh mengalahkan correctness dalam interpretasi.

---

## Experimental Matrix

```text
4 treatments
×
4 failure points
=
16 conditions
```

Target repetitions:

```text
5–10 per condition
```

Final repetitions dibekukan setelah pilot.

Contoh 8 repetitions:

```text
16 × 8 = 128 independent runs
```

---

## Pairing dan Randomization

Failure schedule yang sama digunakan untuk B0/B1/B2/P1.

Freeze:
- batch position;
- recording position;
- failure stage;
- random seed.

Treatment order dirandomisasi.

Reset sink state antar independent run.

---

## Reset Protocol

Sebelum run baru:
- reset MinIO target prefix;
- reset Iceberg metadata state;
- reset optional ingestion ledger;
- reset ephemeral checkpoint;
- isolate persistent checkpoint per run/treatment;
- simpan frozen source corpus tanpa perubahan.

---

## Raw Run Log Minimum

```json
{
  "run_id": "...",
  "treatment": "P1",
  "checkpoint": true,
  "idempotence": true,
  "failure_point": "F2",
  "failure_batch_id": 7,
  "failure_record_index": 143,
  "reprocessed_recordings": 300,
  "reprocessed_bytes": 1234567890,
  "recovery_time_sec": 48.3,
  "completion_time_sec": 212.7,
  "missing": 0,
  "duplicates": 0,
  "orphans": 0,
  "dangling": 0,
  "checksum_mismatch": 0,
  "extras": 0,
  "exact_recovery": true
}
```

Failed runs tetap disimpan.

---

## Analisis Statistik

### Exact Recovery

Binary per run. Laporkan:
- numerator;
- denominator;
- proportion;
- confidence interval.

### Error Counts

Laporkan:
- median;
- IQR;
- mean bila berguna;
- paired bootstrap 95% CI.

### Reprocessing dan Recovery Time

Gunakan paired bootstrap atau non-parametric paired comparison karena distribusi dapat right-skewed.

### Factorial Analysis

Harus membaca:

```text
main effect checkpoint
main effect idempotence
checkpoint × idempotence interaction
failure-point dependence
```

Jangan hanya membuat empat bar chart.

### Unit Statistik

Gunakan independent failure run, bukan setiap file.

---

## Eksperimen E0 — Ground Truth & No-Failure Sanity

- freeze corpus;
- build manifest;
- compute checksum;
- run B0/B1/B2/P1 pada F0;
- reconcile I1–I7.

Gate: seluruh F0 exact.

---

## Eksperimen E1 — Worker Failure

Run F1 pada batch/record yang sama.

Audit:
- orphan;
- duplicate;
- missing;
- checksum;
- task retries.

---

## Eksperimen E2 — Restart Before Checkpoint Commit

Run F2.

Audit:
- replay breadth;
- final correctness;
- metadata duplicate;
- repeated object side effects;
- reprocessed bytes.

---

## Eksperimen E3 — Restart After Checkpoint Commit

Run F3 untuk validasi semantics persistent checkpoint.

---

## Eksperimen E4 — Reprocessing Cost

Fokus B2 vs P1 setelah correctness dibandingkan.

Pertanyaan:

```text
apakah checkpoint mengurangi replay
ketika idempotence sudah menjaga final state?
```

---

## Eksperimen E5 — Failure Analysis

Audit minimal 20 kasus:
- object duplicate;
- orphan;
- metadata duplicate;
- dangling;
- checksum mismatch;
- checkpoint replay;
- failed MERGE;
- incomplete upload;
- fault injector error;
- reset contamination.

---

## Eksperimen E6 — Clean Reproduction

Dari environment bersih, reproduce minimal:
- satu main correctness table;
- satu recovery-cost figure.

Gunakan corpus/checksum/fault plan/software version yang sama.

---

## Quality Gate — Dataset

- [ ] corpus frozen;
- [ ] recording_id stable;
- [ ] SHA-256 lengkap;
- [ ] expected object URI frozen;
- [ ] expected metadata frozen;
- [ ] input order frozen;
- [ ] batch composition frozen.

---

## Quality Gate — Treatment Isolation

- [ ] B0 = checkpoint off, idempotence off.
- [ ] B1 = checkpoint on, idempotence off.
- [ ] B2 = checkpoint off, idempotence on.
- [ ] P1 = checkpoint on, idempotence on.
- [ ] source identical.
- [ ] batching identical.
- [ ] writer identical.
- [ ] hardware identical.
- [ ] software versions identical.

---

## Quality Gate — Failure Injection

- [ ] F0 reproducible.
- [ ] F1 reproducible.
- [ ] F2 reproducible.
- [ ] F3 reproducible.
- [ ] batch position frozen.
- [ ] record position frozen.
- [ ] process/container target logged.
- [ ] minimal satu real process/container kill dilakukan.

---

## Quality Gate — Correctness

- [ ] I1 otomatis.
- [ ] I2 otomatis.
- [ ] I3 otomatis.
- [ ] I4 otomatis.
- [ ] I5 otomatis.
- [ ] I6 otomatis.
- [ ] I7 otomatis.
- [ ] exact recovery dihitung dari I1–I7.

---

## Quality Gate — Main Experiment

- [ ] semua F0 exact;
- [ ] pilot selesai;
- [ ] repetitions frozen;
- [ ] fault plans frozen;
- [ ] order randomized;
- [ ] sink reset antar-run;
- [ ] object listing tersimpan;
- [ ] metadata snapshot tersimpan;
- [ ] checkpoint state tersimpan;
- [ ] Spark event logs tersimpan;
- [ ] failed runs tetap dilaporkan;
- [ ] tidak ada silent rerun/cherry-pick.

---

## Quality Gate — Artikel

- [ ] final related-work search 2021–2026 selesai;
- [ ] novelty tidak mengklaim checkpoint/idempotence sebagai konsep baru;
- [ ] `exactly-once` hanya digunakan jika dual-state equivalence terbukti;
- [ ] failure boundary didokumentasikan;
- [ ] baseline bukan strawman;
- [ ] correctness primer;
- [ ] runtime sekunder;
- [ ] factorial interaction dianalisis;
- [ ] satu main table reproducible;
- [ ] satu main figure reproducible;
- [ ] external validity dibatasi pada immutable object-based ingestion.

---

## Threats to Validity

### Failure Realism

Injected failure tidak identik dengan host crash/network partition.

Mitigasi: deterministic injection + minimal satu real process/container kill.

### Checkpoint Identifiability

Worker-only failure dapat membuat checkpoint tampak tidak relevan.

Mitigasi: F2 dan F3.

### Sink Semantics

MinIO PUT dan Iceberg commit memiliki semantics berbeda. Jangan mengklaim atomicity lintas sistem.

### Baseline Fairness

B0 harus masuk akal, bukan sengaja lemah.

### Corpus Scale

Klaim dibatasi pada tested file count/GB dan resource budget.

### Object Immutability

WAV immutable. Hasil tidak otomatis berlaku ke mutable-record workflow.

### Checksum Cost

SHA-256 dapat menambah CPU/I/O. Precompute source hash.

### Cache/Order Effects

Gunakan reset protocol dan randomized treatment order.

---

## Grafik dan Tabel Wajib

1. Dataset manifest table.
2. Treatment semantics table.
3. Commit/failure boundary diagram.
4. Correctness heatmap strategy × failure point.
5. Exact Recovery Rate + 95% CI.
6. Missing/duplicate/orphan/dangling/checksum breakdown.
7. Reprocessed files/bytes plot.
8. Recovery time B2 vs P1.
9. Factorial checkpoint × idempotence interaction plot.
10. Failure taxonomy table minimal 20 kasus.
11. Publication-boundary table.

---

## Struktur Artikel

1. Introduction.
2. Background.
3. Related Work.
4. Dataset and Testbed.
5. Method.
6. Failure Injection Protocol.
7. Results.
8. Recovery Cost.
9. Mechanism and Failure Analysis.
10. Threats to Validity.
11. Conclusion.

---

# Rencana Kerja 1 Bulan — Pembagian Hari

## Hari 1 — Freeze RQ dan Scope

- freeze RQ utama;
- freeze sub-RQ;
- freeze publication boundary;
- buat research logbook;
- larang penggunaan `exactly-once` sebelum bukti end-to-end tersedia.

Output:

```text
RQ v1
scope v1
claim boundary v1
```

## Hari 2 — Freeze Corpus AudioMoth

- inventaris seluruh WAV;
- pilih corpus penuh/subset;
- freeze file count;
- freeze total GB;
- freeze input order;
- freeze device coverage.

Output:

```text
corpus v1
```

## Hari 3 — Ground-Truth Manifest

- generate recording_id;
- device_id;
- start_time;
- source_path;
- file size;
- expected object URI;
- expected metadata.

## Hari 4 — SHA-256 dan Manifest Audit

- hash seluruh WAV;
- cek missing hash;
- cek duplicate recording_id;
- freeze checksum manifest.

## Hari 5 — Deploy Environment

- Spark;
- MinIO;
- Iceberg;
- durable checkpoint location;
- ephemeral mode;
- Docker Compose;
- freeze software versions/resource caps.

## Hari 6 — Implement B0

- checkpoint OFF;
- idempotence OFF;
- naive at-least-once yang realistis.

## Hari 7 — Implement B1

- checkpoint ON;
- idempotence OFF;
- verifikasi hanya checkpoint switch yang berubah.

## Hari 8 — Implement B2

- checkpoint OFF;
- idempotence ON;
- deterministic key;
- checksum guard;
- metadata MERGE/upsert.

## Hari 9 — Implement P1

- checkpoint ON;
- idempotence ON;
- audit treatment isolation B0/B1/B2/P1.

## Hari 10 — Reconciliation I1–I2

Implement:
- completeness;
- uniqueness.

## Hari 11 — Reconciliation I3–I5

Implement:
- referential consistency;
- no orphan;
- no dangling.

## Hari 12 — Reconciliation I6–I7

Implement:
- byte integrity;
- no extras;
- exact recovery summary.

## Hari 13 — No-Failure Sanity

Run:

```text
B0/F0
B1/F0
B2/F0
P1/F0
```

Semua harus exact. Jika tidak, jangan lanjut.

## Hari 14 — Implement F1

Failure:

```text
after object PUT
before metadata commit
```

Pilot 1–2 runs, freeze trigger.

## Hari 15 — Implement F2

Failure:

```text
after metadata commit
before checkpoint commit
```

Gunakan driver/process restart.

## Hari 16 — Implement F3

Failure:

```text
after checkpoint commit
```

Pilot dan freeze.

## Hari 17 — Pilot Variance dan Repetition Decision

- run paired pilot;
- ukur runtime;
- estimasi variance;
- tetapkan 5–10 repetitions;
- freeze repetitions;
- freeze randomization seed;
- freeze primary endpoints.

## Hari 18 — Main Matrix Block 1

Run B0/B1 × F0/F1 sesuai randomized schedule.

## Hari 19 — Main Matrix Block 2

Run B2/P1 × F0/F1.

## Hari 20 — Main Matrix Block 3

Run B0/B1 × F2/F3.

## Hari 21 — Main Matrix Block 4

Run B2/P1 × F2/F3.

## Hari 22 — Complete Planned Repetitions

- selesaikan target repetitions;
- jangan ubah failure timing;
- jangan cherry-pick;
- simpan failed runs.

Freeze `raw results v1`.

## Hari 23 — Correctness Analysis

Hitung:
- missing;
- duplicate;
- orphan;
- dangling;
- checksum mismatch;
- extras;
- Exact Recovery Rate.

## Hari 24 — Recovery-Cost Analysis

Hitung:
- reprocessed files;
- reprocessed bytes;
- recovery time;
- completion time;
- task attempts;
- checkpoint overhead.

## Hari 25 — Factorial Analysis

Analisis:

```text
checkpoint main effect
idempotence main effect
checkpoint × idempotence interaction
failure-point dependence
```

Lakukan paired bootstrap 95% CI.

## Hari 26 — Failure Analysis

Audit minimal 20 cases dan buat taxonomy.

## Hari 27 — Robustness dengan Real Kill

Lakukan minimal satu actual driver/container kill dan bandingkan arah hasil dengan staged injection.

## Hari 28 — Clean Reproduction

Dari clean environment:
- same corpus;
- same checksum;
- same fault plan;
- same configs;
- reproduce satu main correctness table;
- reproduce satu main cost figure.

## Hari 29 — Penulisan Artikel

Tulis:
- Method;
- Failure Protocol;
- Results;
- Recovery Cost;
- Failure Analysis;
- Threats to Validity.

Lakukan final literature verification 2021–2026.

## Hari 30 — Freeze Artifact

Freeze:
- code revision;
- corpus manifest;
- checksums;
- versions;
- resource caps;
- treatment configs;
- fault plans;
- raw results;
- tables;
- figures;
- manuscript v0.8–v1.0.

Supervisor/internal review.

---

## Definition of Done — Bulan Pertama

- [ ] corpus frozen;
- [ ] SHA-256 lengkap;
- [ ] B0/B1/B2/P1 implemented;
- [ ] treatment isolation verified;
- [ ] I1–I7 implemented;
- [ ] F0/F1/F2/F3 reproducible;
- [ ] seluruh no-failure runs exact;
- [ ] repetitions frozen after pilot;
- [ ] full main matrix complete;
- [ ] correctness table complete;
- [ ] Exact Recovery Rate complete;
- [ ] recovery-cost analysis complete;
- [ ] factorial analysis complete;
- [ ] minimal 20 failure/anomaly cases audited;
- [ ] minimal satu real kill robustness selesai;
- [ ] clean reproduction selesai;
- [ ] satu main table reproducible;
- [ ] satu main figure reproducible;
- [ ] manuscript v0.8–v1.0 tersedia.

---

## Struktur Repository

```text
DSIC-2606/
└── checkpointing-idempotent-audiomoth-ingestion/
    ├── README.md
    ├── .gitignore
    ├── .env.example
    ├── pyproject.toml
    ├── requirements.txt
    ├── Makefile
    ├── docker-compose.yml
    ├── configs/
    │   ├── environment.yaml
    │   ├── dataset.yaml
    │   ├── batching.yaml
    │   ├── treatments.yaml
    │   ├── checkpoint.yaml
    │   ├── idempotence.yaml
    │   ├── faults.yaml
    │   ├── experiment.yaml
    │   ├── reconciliation.yaml
    │   └── analysis.yaml
    ├── infra/
    │   ├── spark/
    │   ├── minio/
    │   ├── iceberg/
    │   └── trino/
    ├── data/
    │   ├── raw/audiomoth/
    │   ├── manifests/
    │   ├── ground_truth/
    │   ├── checkpoints/
    │   │   ├── persistent/
    │   │   └── ephemeral/
    │   ├── staging/
    │   └── sink/
    │       ├── objects/
    │       └── metadata/
    ├── schemas/
    ├── fault_plans/
    ├── src/
    │   ├── manifest/
    │   ├── ingestion/
    │   ├── idempotence/
    │   ├── checkpointing/
    │   ├── fault_injection/
    │   ├── reconciliation/
    │   ├── evaluation/
    │   └── utils/
    ├── tests/
    ├── scripts/
    ├── results/
    │   ├── raw/
    │   ├── processed/
    │   ├── figures/
    │   ├── tables/
    │   └── failure_cases/
    ├── docs/
    └── paper/
```

---

## Catatan Pembimbing

Alur besarnya kira-kira seperti ini:

```text
Frozen AudioMoth WAV Corpus
        ↓
buat immutable ground-truth manifest
recording_id | device_id | start_time
size | SHA-256 | expected object | expected metadata
        ↓
freeze input order + micro-batches
        ↓
Spark Structured Streaming
        ↓
2×2 treatment
checkpoint OFF/ON
idempotence OFF/ON
        ↓
B0 | B1 | B2 | P1
        ↓
MinIO object write
        ↓
Iceberg metadata commit
        ↓
checkpoint commit
        ↓
inject F0 | F1 | F2 | F3
        ↓
retry / restart
        ↓
reconciliation auditor
        ↓
I1 completeness
I2 uniqueness
I3 referential consistency
I4 no orphan
I5 no dangling
I6 byte integrity
I7 no extras
        ↓
Exact Recovery Rate
        ↓
reprocessed files / bytes
recovery time
retry attempts
        ↓
factorial analysis
checkpoint × idempotence
        ↓
failure taxonomy
        ↓
clean reproduction
```

Secara eksperimen bisa dipahami seperti berikut.

1. **Mulai dari ground truth, bukan dari Spark.** Freeze corpus AudioMoth dan buat manifest immutable terlebih dahulu. Tanpa manifest, kita tidak bisa membuktikan state akhir benar.

2. **Audio tidak dianalisis secara bioakustik.** WAV hanyalah immutable object. Penelitian ini Data Systems, bukan species recognition.

3. **Bangun satu pipeline yang sama untuk seluruh treatment.** Source replay, batching, object writer, metadata writer, hardware, software version, dan corpus harus sama. Yang berubah hanya checkpoint dan idempotence switches.

4. **Buat empat treatment.** B0 memberi baseline at-least-once naive; B1 mengisolasi checkpoint; B2 mengisolasi idempotence; P1 menguji kombinasi.

5. **Checkpoint dan idempotence mengatasi failure surface berbeda.** Checkpoint menyimpan progress. Idempotence menjaga repeated side effect tetap converge. Jangan menyamakan keduanya.

6. **Idempotence harus melindungi object dan metadata.** Stable object key saja tidak cukup jika metadata masih append-duplicate. Metadata MERGE saja tidak cukup jika object key berubah tiap replay.

7. **F0 wajib exact.** Kalau kondisi tanpa failure sudah menghasilkan duplicate, missing, atau checksum mismatch, eksperimen failure tidak boleh dipakai.

8. **F1 terutama menguji task retry dan object-side idempotence.** Failure terjadi sesudah object side effect tetapi sebelum metadata commit.

9. **F2 paling penting untuk checkpoint.** Metadata sudah committed tetapi checkpoint belum durable. Driver restart dapat memicu replay terhadap side effect yang sudah terjadi.

10. **F3 memvalidasi checkpoint semantics.** Setelah checkpoint committed, restart seharusnya tidak mengulang committed batch secara material pada B1/P1.

11. **Failure harus reproducible.** Gunakan fault plan yang menyebut batch dan record position. Jangan kill manual acak sebagai main experiment.

12. **Minimal satu real kill tetap dilakukan.** Ini robustness check terhadap kemungkinan injected exception terlalu artifisial.

13. **Setiap run harus direkonsiliasi.** Hitung I1–I7 secara otomatis. Jangan mengandalkan pemeriksaan manual sebagai primary correctness evidence.

14. **Exact Recovery Rate adalah endpoint utama.** Runtime cepat tidak berarti benar.

15. **B2 vs P1 memberi pertanyaan cost yang menarik.** Jika keduanya exact, apakah checkpoint mengurangi replay breadth dan recovery cost?

16. **Gunakan paired failure schedule.** B0/B1/B2/P1 harus gagal pada batch/record yang sama.

17. **Reset sink antar-run.** Sisa object atau metadata dari run sebelumnya dapat menciptakan false duplicate atau false recovery.

18. **Randomisasi treatment order.** Ini mengurangi cache, order, dan thermal bias.

19. **Jangan mengubah idempotence rule setelah melihat failure case.** Rule harus dibekukan sebelum main matrix.

20. **Analisis harus factorial.** Reviewer harus bisa melihat apa efek checkpoint, apa efek idempotence, dan apakah keduanya berinteraksi.

21. **Hasil nol tetap valid.** Misalnya checkpoint-only ternyata exact pada seluruh tested failures. Jelaskan sink semantics dan boundary yang membuatnya terjadi.

22. **Failure analysis harus menjelaskan mekanisme.** Jangan berhenti pada jumlah error. Kaitkan error dengan sequence object PUT → metadata commit → checkpoint commit → replay.

23. **Clean reproduction wajib.** Artifact harus mampu membangun kembali minimal satu main table dan satu main figure.

24. **Jaga bahasa klaim.** Istilah utama adalah `post-recovery correctness` dan `exact recovery`. `Exactly-once` hanya digunakan jika benar-benar dibuktikan end-to-end pada tested failure model.

Yang paling penting: penelitian DSIC-2606 bukan **“apakah pipeline dapat restart?”**, tetapi **“setelah failure dan replay, apakah setiap recording AudioMoth kembali menjadi satu canonical WAV object dengan bytes yang benar dan satu metadata record yang konsisten, serta apa peran checkpointing dan idempotence untuk mencapai state tersebut?”**
