# Provenans Perangkat AudioMoth

Dokumen ini merangkum identitas perangkat dan pengaturan waktu berdasarkan empat berkas `CONFIG.TXT` untuk sesi Main, Kantin, Embung D, dan Kebun Raya. Catatan konfirmasi zona waktu dari pembimbing juga dicantumkan agar dasar konversi timestamp dapat ditelusuri.

## Identitas perangkat fisik

- **Device ID fisik:** `242A260460377E01`
- **Firmware:** `AudioMoth-Firmware-Basic (1.12.1)`
- **Jumlah perangkat fisik:** 1, berdasarkan jumlah Device ID unik pada empat `CONFIG.TXT` yang diperiksa.
- Keempat konfigurasi mencatat `Use device ID in WAV file name: No`; nama berkas tidak menyertakan Device ID fisik.

## Konfigurasi sesi dan pemeriksaan nama berkas

| Sesi | Berkas konfigurasi | Device time pada CONFIG.TXT | Jadwal rekam pada CONFIG.TXT (UTC+7) | WAV pertama yang diperiksa |
|---|---|---|---|---|
| Main | `data/raw/audiomoth/main/CONFIG.TXT` | 2026-09-24 18:32:29 (UTC+7) | 13:30–18:30 | `20260924_133000.WAV` |
| Kantin | `data/raw/audiomoth/robustness/kantin/CONFIG.TXT` | 2026-09-23 12:01:43 (UTC+7) | 10:00–12:00 | `20260923_100000.WAV` |
| Embung D | `data/raw/audiomoth/robustness/embung d/CONFIG.TXT` | 2026-09-25 13:58:27 (UTC+7) | 12:10–13:50 | `20260925_121000.WAV` |
| Kebun Raya | `data/raw/audiomoth/robustness/kebun raya/CONFIG.TXT` | 2026-09-24 11:06:15 (UTC+7) | 11:10–12:50 | `20260924_111000.WAV` |

Pada setiap sesi, timestamp nama WAV pertama cocok dengan waktu mulai jadwal yang dicatat di `CONFIG.TXT` dalam UTC+7. Ini merupakan bukti pencocokan antara konfigurasi jadwal dan nama berkas; `CONFIG.TXT` sendiri menyatakan zona waktu perangkat/jadwal, bukan aturan format nama berkas secara terpisah.

## Dasar zona waktu metadata

Pak Dika mengonfirmasi pada **23 September 2026** bahwa perangkat menggunakan waktu lokal UTC+7 saat perekaman. Karena itu, timestamp pada nama berkas diperlakukan sebagai waktu lokal `Asia/Jakarta`, lalu dinormalisasi ke UTC pada kolom `start_time` manifest. Contoh: `20260924_133000.WAV` menunjukkan waktu jadwal 13:30 UTC+7, yang direpresentasikan sebagai `2026-09-24T06:30:00Z` di manifest.

## Hubungan dengan identitas metadata

Pada manifest saat ini, `device_id` berisi label sesi seperti `MAIN_5JAM`, bukan Device ID fisik. Aturan generator yang berlaku membentuk `recording_id` dari gabungan label sesi dan nama dasar berkas (`{device_id}_{filename_stem}`). Device ID fisik dicatat di dokumen provenans ini dan tidak menggantikan label sesi pada manifest. Dengan demikian, pencatatan provenans ini tidak mengubah `recording_id` selama label sesi dan aturan pembentukannya tetap.

## Berkas sumber

Salinan sumber `CONFIG.TXT` yang diperiksa berada pada empat path di kolom **Berkas konfigurasi**. Status penambahan/commit berkas-berkas sumber tersebut ke Git perlu dipastikan melalui `git status` sebelum gate provenans dinyatakan selesai.
