# Semantik Checkpoint B0 dan B1

## Apa yang disimpan checkpoint

Checkpoint Spark Structured Streaming menyimpan informasi progres pemrosesan agar driver dapat mengetahui posisi dan keadaan stream saat pekerjaan dilanjutkan. Dalam eksperimen ini, kedua treatment memakai lokasi checkpoint yang eksplisit.

## B0: checkpoint sementara

B0 adalah baseline at-least-once tanpa perlindungan idempotence. Istilah **OFF** pada B0 bukan berarti Spark tidak membuat atau memakai direktori checkpoint. Artinya, checkpoint diarahkan ke penyimpanan sementara di dalam kontainer driver:

```text
{ephemeral_root}/{run_id}/{treatment}
```

Dengan akar instrumen `/checkpoints/ephemeral`, contoh path untuk `pilot-001` adalah `/checkpoints/ephemeral/pilot-001/B0`. Akar ini memakai `tmpfs` milik kontainer. Isinya hilang ketika kontainer driver dihapus.

## B1: checkpoint persisten

B1 memakai template path per-run yang sama, tetapi di bawah akar persisten:

```text
{persistent_root}/{run_id}/{treatment}
```

Dengan akar instrumen `/checkpoints/persistent`, contoh path untuk `pilot-001` adalah `/checkpoints/persistent/pilot-001/B1`. Akar ini berada pada bind mount disk VM sehingga checkpoint bertahan ketika kontainer driver diganti.

## Batas perbandingan treatment

Lokasi checkpoint adalah satu-satunya kunci konfigurasi yang membedakan B0 dan B1. Akar checkpoint tidak ditempatkan di MinIO; MinIO adalah object storage/sink yang diuji, sedangkan checkpoint disimpan pada volume sementara atau disk VM sesuai treatment. Self-test instrumen T5a–T5c memverifikasi penanda persistent bertahan, penanda ephemeral hilang pada kontainer baru, dan mount ephemeral bertipe `tmpfs`.

Perbedaan ini menjelaskan daya tahan checkpoint yang diuji. Ia sendiri belum menyatakan hasil B0/B1 pada korpus; hasil tersebut baru diketahui setelah pipeline ingesti dijalankan dan diperiksa.
