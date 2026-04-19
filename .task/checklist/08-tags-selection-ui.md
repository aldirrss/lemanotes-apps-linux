# Feature: Tag Selection UI

## Status: DONE ✅

## Goal
Ganti UI input tag dari text field bebas menjadi sistem selection yang lebih
bagus: dropdown/popup menampilkan semua tag yang sudah ada di seluruh notebook,
user bisa pilih tag existing atau ketik baru, dengan tampilan pill yang konsisten.

---

## Checklist

### Data Layer
- [ ] `storage.get_all_tags()` — kumpulkan semua tag unik dari seluruh notebook
  (scan semua `.meta.json`, return `sorted(set(...))`)

### TagBar Redesign
- [ ] Hapus `QLineEdit` text input langsung dari `TagBar`
- [ ] Ganti dengan tombol `+ Add tag` kecil yang membuka tag picker popup
- [ ] `TagPill` tetap ada untuk menampilkan tag yang sudah ditambahkan
- [ ] Tombol `×` di setiap pill untuk hapus tag (sudah ada, pastikan tetap berfungsi)

### TagPickerPopup (QFrame popup)
- [ ] `TagPickerPopup(QFrame)` — popup muncul di bawah tombol `+ Add tag`
- [ ] `QLineEdit` search/filter di atas popup (autofocus saat popup terbuka)
- [ ] `QListWidget` di bawahnya — menampilkan semua tag existing yang sudah ada
- [ ] Filter list secara live saat user mengetik di search box
- [ ] Klik item di list → tambahkan tag, tutup popup
- [ ] Jika teks di search box tidak ada di list → tampilkan item `+ Create "teks"` di bagian bawah list
- [ ] Klik `+ Create "teks"` → buat tag baru dari teks tersebut, tambahkan ke note, tutup popup
- [ ] `Enter` key → pilih item pertama di list (atau create jika tidak ada match)
- [ ] `Escape` key → tutup popup tanpa aksi
- [ ] Klik di luar popup → tutup popup (gunakan `Qt.WindowType.Popup` atau event filter)
- [ ] Tidak menampilkan tag yang sudah ada di note saat ini (sudah dipilih)

### Styling
- [ ] Popup background mengikuti theme (`bg2`, `border`)
- [ ] Item list: hover state dengan `item_hover`, selected dengan `item_sel`
- [ ] Search box styling konsisten dengan theme (sama seperti search bar di `NoteListPanel`)
- [ ] `+ Create "teks"` item ditampilkan dengan warna `accent` / italic agar beda
- [ ] Lebar popup minimal sama dengan tombol `+ Add tag`, max ~250px

### Integrasi
- [ ] `TagBar.apply_theme(t)` memperbarui style popup jika sedang terbuka
- [ ] `TagBar` emit `tags_changed` saat tag ditambah/dihapus (sudah ada, pastikan tetap)
- [ ] `EditorPanel` memanggil `storage.get_all_tags(nb)` saat `load_note()` dan
  meneruskan ke `TagBar` sebagai daftar suggestion
- [ ] Tag baru yang dibuat langsung masuk ke suggestion list untuk sesi tersebut

### Edge Cases
- [ ] Notebook kosong (belum ada tag sama sekali) → popup hanya tampilkan search box + create option
- [ ] Semua tag existing sudah ditambahkan ke note → list kosong, hanya tampilkan create
- [ ] Tag dengan karakter spesial (spasi, tanda baca) tetap berfungsi
- [ ] Popup tidak keluar dari batas layar (posisi disesuaikan jika terlalu ke bawah)
