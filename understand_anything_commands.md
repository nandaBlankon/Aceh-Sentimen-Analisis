# Panduan Perintah Understand-Anything

Berikut adalah daftar perintah untuk menjalankan dan menggunakan **Understand-Anything** di dalam chat/AI Assistant:

## 1. Memulai Analisis (Wajib untuk pertama kali)
Memindai seluruh proyek Anda dan membuat *knowledge graph*.
```bash
/understand
```
> **Tips**: Gunakan flag bahasa jika ingin output (penjelasan graph) dalam bahasa Indonesia:
> ```bash
> /understand --language id
> ```

## 2. Membuka Dashboard Visual
Setelah proses analisis selesai, buka dashboard interaktif untuk melihat visualisasi arsitektur kode Anda.
```bash
/understand-dashboard
```

## 3. Perintah Tambahan (Eksplorasi Lanjutan)
- **`/understand-chat <pertanyaan>`** : Bertanya spesifik tentang codebase Anda (contoh: `/understand-chat bagaimana alur login bekerja?`).
- **`/understand-domain`** : Menganalisis dan mengekstrak logika bisnis dan domain proses.
- **`/understand-explain <path/ke/file>`** : Meminta penjelasan mendalam untuk satu file atau fungsi tertentu.
- **`/understand-diff`** : Menganalisis dampak dari perubahan kode yang sedang Anda buat sebelum melakukan *commit*.

---
**Catatan Penting:** 
Jika saat Anda mengetik `/understand` sistem tidak mengenalinya, **restart (tutup dan buka kembali) IDE / AI Assistant ini** terlebih dahulu agar plugin yang baru di-install bisa termuat dengan sempurna.
