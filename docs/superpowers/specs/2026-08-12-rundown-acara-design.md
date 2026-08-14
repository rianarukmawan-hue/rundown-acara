# Spesifikasi Desain: Aplikasi Susunan Acara ("Rundown Acara")

Tanggal: 2026-08-12
Status: Disetujui oleh pengguna (diperbarui 2026-08-12: cetak/PDF & PWA; diperbarui 2026-08-14: berbagi link terkompresi + QR)

## 1. Ringkasan

Aplikasi web untuk **membuat dan mengatur susunan acara** (rundown) berdasarkan waktu. Pengguna mengelola daftar sesi dengan jam mulai & durasi, dan dapat menampilkan rundown secara live di layar/proyektor selama acara berlangsung. Rundown dapat **dibagikan** ke perangkat lain lewat link terkompresi atau kode QR — tanpa server. Aplikasi inti berbentuk satu file `index.html` (tanpa build/dependensi) yang dikemas sebagai **PWA** — bisa di-install di HP dengan ikon sendiri, berjalan layar penuh, dan tetap bisa dibuka saat offline.

## 2. Kebutuhan (dari klarifikasi)

1. **Platform:** web app di browser, responsif untuk HP dan laptop.
2. **Model waktu:** setiap sesi memiliki jam mulai dan durasi. Default: waktu mulai **menyambung otomatis** dari sesi sebelumnya; setiap sesi bisa **di-pin** ke jam mulai tertentu.
3. **Penyimpanan:** otomatis di browser (localStorage) + export/import file JSON.
4. **Fitur sesi:** nama, durasi, PIC/penanggung jawab, catatan, bagian/kategori berwarna (mis. Pembukaan, Acara Inti, Penutup), dan tanda **istirahat** (break).
5. **Mode tampil (live):** tampilan besar & bersih untuk proyektor — menyorot sesi yang sedang berjalan, countdown ke sesi non-istirahat berikutnya, sinkron dengan jam nyata.
6. **PWA:** bisa di-install di HP (manifest + ikon + service worker untuk offline) dan mode layar penuh.
7. **Berbagi rundown:** menghasilkan link pendek berisi seluruh data rundown (terkompresi) + kode QR yang bisa dipindai; penerima membuka link dan rundown dimuat di perangkatnya.

## 3. Arsitektur

Aplikasi inti: satu file `index.html` berisi HTML + CSS + JavaScript vanilla — tanpa framework, tanpa build, tanpa dependensi eksternal (selain Google Fonts untuk tipografi). Aplikasi dibungkus sebagai PWA dengan beberapa file pendukung:

| File | Peran |
|---|---|
| `index.html` | Aplikasi utama (editor + mode live, localStorage, export/import, cetak/PDF, berbagi link + QR). Memuat manifest & ikon, dan mendaftarkan service worker. |
| `manifest.webmanifest` | Manifest PWA: nama, ikon, warna tema, `display: standalone` → tampil seperti aplikasi asli saat di-install. |
| `sw.js` | Service worker: cache aset statis untuk offline; strategi network-first untuk navigasi agar update cepat. |
| `icon-180.png`, `icon-192.png`, `icon-512.png` | Ikon aplikasi (PNG) — dipakai manifest, favicon, dan `apple-touch-icon`. |
| `tools/generate_icons.py` | Generator ikon (stdlib Python saja) — jalankan ulang jika ingin mengubah desain ikon. |

Catatan penting: service worker dan instalasi PWA hanya aktif saat aplikasi disajikan melalui **HTTPS** atau **localhost** (tidak dari `file://`). Saat dibuka langsung sebagai file, seluruh fungsi editor tetap berjalan normal — hanya fitur PWA yang nonaktif.

Fitur berbagi juga **inline di `index.html`** (tanpa dependensi eksternal):

- **Kompresi link** — port dari pustaka lz-string (algoritma LZ, `compressToEncodedURIComponent`, perilaku versi 1.4.5) yang menghasilkan output **byte-identik** dengan pustaka asli sehingga bisa saling decode.
- **Encoder QR offline** — encoder kode QR dari nol (mode byte, level koreksi M, versi 1–40 otomatis, pemilihan mask dengan penalti minimum) yang menghasilkan SVG tanpa pustaka pihak ketiga.

Dua mode dalam satu layar:

- **Mode Editor** — kelola rundown (tambah/edit/hapus/urutkan sesi, atur judul & jam mulai acara, export/import, cetak/PDF).
- **Mode Tampil (Live)** — tampilan besar untuk proyektor; menyorot sesi berjalan, countdown, mengikuti jam nyata; dukungan layar penuh.

## 4. Model Data

Disimpan di localStorage (kunci: `rundownAcara.v1`) sebagai JSON:

```js
{
  judulAcara: string,          // judul acara (default "Susunan Acara")
  jamMulaiAcara: "HH:MM",      // patokan waktu acara pertama
  sesi: [
    {
      id: string,              // unik (crypto.randomUUID / fallback)
      nama: string,
      durasiMenit: number,     // >= 0
      pic: string,
      catatan: string,
      bagian: string,          // nama bagian; warna otomatis dari palet
      isIstirahat: boolean,
      pinnedJam: "HH:MM" | null // null = mengikuti otomatis; nilai = pin ke jam itu
    }
  ]
}
```

Aturan penting:

- Waktu mulai sesi **tidak disimpan** — selalu dihitung ulang dari `jamMulaiAcara` + akumulasi durasi, kecuali sesi yang di-pin.
- Urutan sesi = urutan array (diubah via tombol naik/turun).
- `bagian` adalah string bebas; setiap bagian unik mendapat warna dari palet (rotasi). Istirahat selalu ditampilkan dengan gaya sendiri.
- Versi kunci localStorage memungkinkan migrasi format di masa depan.

## 5. Logika Waktu

### Perhitungan berantai

1. `jamMulaiAcara` menjadi patokan sesi pertama.
2. Untuk setiap sesi berurutan:
   - Jika `pinnedJam` terisi → waktu mulai = `pinnedJam`.
   - Jika tidak → waktu mulai = akhir sesi sebelumnya.
   - Waktu selesai = waktu mulai + durasi.

Catatan: pin menentukan waktu *mulai*; sesi sesudahnya melanjutkan dari akhir sesi yang di-pin (kecuali di-pin juga).

### Perubahan durasi

- Mengubah durasi sesi A → semua sesi setelah A yang tidak di-pin otomatis bergeser.
- Mengubah jam mulai acara → seluruh rantai bergeser (kecuali sesi yang di-pin).

### Mode Live

- Timer berjalan setiap detik.
- Sesi **aktif** = jam mulai ≤ waktu sekarang < jam selesai.
- Countdown menunjuk **sesi non-istirahat berikutnya** yang belum dimulai. Sesi istirahat dilewati sebagai target countdown (tapi tetap ditampilkan di daftar).
- Kondisi khusus: jika acara belum dimulai → countdown menuju sesi pertama; jika acara selesai → tampil status "Acara selesai".

## 6. Tampilan (UI)

Design system dari ui-ux-pro-max ("Soft UI Evolution"):

- **Primer:** `#7C3AED` (ungu), **Sekunder:** `#A78BFA`, **CTA/aksen:** `#F97316` (oranye, untuk countdown & aksi utama), **Latar:** `#FAF5FF`, **Teks:** `#4C1D95`.
- **Tipografi:** Bebas Neue (judul), Source Sans 3 (isi). Google Fonts via `@import`.
- **Efek:** bayangan lembut, transisi 150–300ms, focus visible, WCAG AA (kontras ≥ 4.5:1), hormati `prefers-reduced-motion`.
- **Ikon:** SVG inline (Lucide/Heroicons-style), tanpa emoji sebagai ikon.
- Semua elemen interaktif: `cursor-pointer`, hover feedback, ukuran sentuh ≥ 44px.

### Mode Editor

- **Bar atas:** judul acara (editable), input jam mulai acara, tombol **Import**, **Export**, **Cetak / PDF**, **Bagikan**, tombol besar oranye **Mode Tampil**, dan tombol **Pasang** (muncul otomatis saat browser siap meng-install PWA).
- **Daftar sesi:** kartu per sesi, aksen warna sesuai bagian:
  - nama sesi, jam mulai (hasil hitung), durasi (input menit), PIC, catatan;
  - toggle **Istirahat**;
  - ikon pin untuk mengunci jam mulai (input jam muncul saat dipin);
  - tombol hapus, kontrol urutan naik/turun;
  - tombol **+ Tambah Sesi** di bawah daftar; tambahan input untuk bagian baru.
- **Ringkasan:** total durasi + jam selesai acara di bawah daftar.
- **Penyimpanan:** otomatis ke localStorage setiap perubahan + indikator kecil "Tersimpan".

### Mode Tampil (Live)

- Latar gelap pekat, font besar (terbaca dari jauh).
- Judul acara + jam sekarang besar di atas.
- Rundown vertikal:
  - sesi **aktif** → tersorot ungu terang, label "BERLANGSUNG";
  - sesi selesai → redup + tanda centang;
  - sesi berikutnya → menonjol dengan **countdown besar** (ke sesi non-istirahat berikutnya);
  - istirahat → ditandai jelas, bukan target countdown.
- Tombol **Layar Penuh** (toggle Fullscreen API, dengan ikon & label yang ikut berubah) dan **Kembali ke Editor**.

### Cetak / PDF

- Tombol **Cetak / PDF** di bar atas editor membuka dialog cetak browser (dengan opsi "Simpan sebagai PDF"); pintasan `Ctrl+P`/`Cmd+P` juga memakai format yang sama (event `beforeprint`).
- Print stylesheet (`@media print`) menyembunyikan editor, mode live, dan toast; hanya dokumen rundown yang tercetak: judul, jam mulai + tanggal cetak, tabel (No | Waktu | Sesi | Durasi | PIC | Catatan), baris istirahat diberi badge, serta footer total durasi & jam selesai.

### Bagikan (Link & QR)

- **Tombol Bagikan** di bar atas editor membuka modal berisi: link lengkap (`<alamat>#d=<data terkompresi>`) yang bisa disalin, tombol **Salin Link**, dan **kode QR** SVG yang di-generate di perangkat (bisa dipindai dari HP).
- **Format link:** data rundown (`JSON.stringify(state)`) dikompresi dengan algoritma LZ yang kompatibel lz-string, di-encode ke alfabet URL-safe (`A–Z a–z 0–9 + - $`), lalu disisipkan sebagai fragment `#d=…` — jadi tidak ada data yang diunggah ke server mana pun.
- **Muat dari link:** saat aplikasi dibuka dengan fragment `#d=`, data didekompresi + divalidasi ulang (reuse validasi import). Jika perangkat **belum punya** data tersimpan → rundown dimuat otomatis. Jika **sudah punya** data → muncul banner konfirmasi *"Ada rundown di link ini"* dengan tombol **Muat** (mengganti data saat ini) atau **Tutup** (menjaga data lama); hash dibersihkan setelah diputuskan.
- **Batas QR:** jika data terkompresi melebihi kapasitas QR versi 40 level M (~2.300 byte), QR tidak ditampilkan dan muncul peringatan untuk memakai **Salin Link** atau **Export JSON**.

### PWA & Instalasi

- **Manifest** (`manifest.webmanifest`): `display: standalone`, `theme_color: #7C3AED`, ikon 192/512 dengan `purpose: any maskable`, `start_url: ./index.html`.
- **Ikon:** persegi penuh ungu `#7C3AED` dengan gelang jam putih + jarum & titik tengah oranye — di-generate oleh `tools/generate_icons.py` (supersampling 4×4 untuk tepi halus).
- **Service worker** (`sw.js`): cache aset saat `install`; hapus cache lama saat `activate`; strategi network-first untuk navigasi dan cache-first untuk aset statis (hanya aset origin sendiri).
- **Instalasi:** mendengarkan `beforeinstallprompt` → tombol **Pasang** muncul; `appinstalled` → toast konfirmasi. Untuk iOS, `apple-touch-icon` + `apple-mobile-web-app-capable`.
- **Layar penuh:** tombol di mode tampil memakai Fullscreen API; jika tidak didukung/ ditolak (mis. iframe), muncul toast keterangan tanpa merusak alur aplikasi.

## 7. Penanganan Error

- **Import JSON:** validasi struktur — wajib ada `sesi` (array), setiap sesi punya `nama` (string) dan `durasiMenit` (angka ≥ 0), jam valid (`HH:MM`). Jika gagal → pesan error jelas, data lama tidak tertimpa.
- **Link `#d=` rusak/tidak valid:** dekompresi gagal atau hasil validasi import tidak lolos → toast error jelas, hash dibersihkan, data yang sudah ada tidak disentuh.
- **Edge case:**
  - sesi tanpa nama → ditampilkan "(Tanpa nama)";
  - rundown kosong → pesan kosong + tombol tambah sesi;
  - pin yang tumpang-tindih dengan sesi lain → dibiarkan (keputusan pengguna), tapi ada keterangan tumpang-tindih/urutan aneh;
  - durasi 0 → sesi instan (mulai = selesai), tetap valid.

## 8. Pengujian

Setelah implementasi, uji manual di preview:

1. Tambah/edit/hapus/urutkan sesi.
2. Ubah durasi → periksa pergeseran otomatis sesi setelahnya.
3. Pin jam mulai → periksa sesi berikutnya melanjutkan dari sana.
4. Toggle istirahat → pastikan tidak jadi target countdown.
5. Export JSON → import ulang → data sama.
6. Import file rusak → error jelas, data tidak hilang.
7. Mode live: sorot sesi berjalan, countdown, status sebelum/sesudah acara.
8. Responsif 375px (HP) dan tampilan lebar (laptop).
9. Cetak/PDF: format dokumen bersih, editor tersembunyi, baris istirahat ditandai.
10. PWA (via server statis / hosting, karena preview hanya menyajikan `index.html`): manifest & ikon tersaji 200, `sw.js` lolos cek sintaks, SW terdaftar, halaman bisa dimuat offline setelah pertama dibuka, dan tombol layar penuh toggle masuk/keluar.
11. Bagikan: modal terbuka, link terbentuk dengan benar, QR ter-generate, salin link berfungsi; QR hasil encoder sendiri bisa di-decode kembali (divalidasi dengan jsQR di versi 1–40, termasuk teks non-ASCII/emoji) dan output kompresi byte-identik dengan pustaka lz-string asli (round-trip dua arah).
12. Muat dari link: perangkat tanpa data → termuat otomatis; perangkat dengan data → banner konfirmasi muncul, tombol Muat mengganti data, tombol Tutup menjaga data lama, dan link rusak ditolak tanpa merusak data.
