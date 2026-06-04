# Aceh Sentimen Analisis (ASA)

Aceh Sentimen Analisis (ASA) adalah sistem pemantauan sentimen publik berbasis kecerdasan buatan (AI) yang mendeteksi dan menganalisis sentimen dari berbagai isu strategis di Provinsi Aceh. Sistem ini mengotomatisasi pengumpulan data dari portal berita lokal dan platform media sosial (seperti TikTok), menganalisis muatan sentimen serta menghasilkan ringkasan eksekutif secara otomatis menggunakan model **Google Gemini 1.5 Flash**, dan menyajikan visualisasinya secara real-time pada dasbor interaktif.

Sistem dasbor dinamis ini memiliki SPA (Single Page Application) routing yang memuat data secara asinkron dari backend REST API FastAPI.

---

## 🚀 Fitur Utama

- **Web Scraping Berita & Media Sosial**: Mengunduh judul, ringkasan berita, dan komentar secara dinamis berdasarkan kata kunci pencarian dari berbagai portal berita melalui integrasi Google News RSS (menggunakan HTTPX asinkron & BeautifulSoup) serta komentar TikTok.
- **Klasifikasi Sentimen AI & Ekstraksi Topik**: Menganalisis teks menggunakan **Google Gemini 1.5 Flash** untuk memetakan sentimen menjadi **positif**, **negatif**, atau **netral** beserta nilai keyakinan (confidence score).
- **Ringkasan Eksekutif AI (Executive Summary)**: AI secara otomatis menyusun ringkasan umum isu, mengumpulkan poin-poin penting dari berita dan opini masyarakat, serta memberikan rekomendasi kebijakan strategis untuk pimpinan daerah.
- **Dasbor Analitik Real-Time**:
  - Filter interaktif berbasis UI (Confidence Score threshold & Filter Sentimen).
  - KPI statistik (total data, persentase sentimen).
  - Komparasi kontribusi data per platform (Berita, TikTok, Meta).
  - Grafik garis Tren Sentimen *Time-Series* (Chart.js).
  - Live Feed berisi kutipan berita real-time lengkap dengan label sentimen.
- **Manajemen Isu Fleksibel**: Memungkinkan penambahan kata kunci pencarian isu baru secara dinamis langsung dari formulir antarmuka pengguna.

---

## 🛠️ Teknologi yang Digunakan

### Backend & AI (Python)
- **FastAPI**: Kerangka kerja web REST API asinkron berperforma tinggi.
- **SQLAlchemy (ORM)**: Pemetaan database objek-relasional untuk transaksi data yang aman dari SQL Injection.
- **Google Generative AI (Gemini 1.5 Flash)**: Model AI canggih untuk klasifikasi sentimen teks dan *generative summarization*.
- **HTTPX**: Klien HTTP asinkron untuk berinteraksi dengan API eksternal secara non-blocking.
- **BeautifulSoup4 & Requests**: Alat parsing HTML DOM dan pengambilan dokumen web untuk web scraping.

### Database
- **PostgreSQL / SQLite**: Penyimpanan relasional terstruktur untuk mengelola data isu dan sentimen hasil analisis.

### Frontend
- **HTML5 & Vanilla JavaScript**: Logika dasbor SPA dengan modifikasi DOM yang aman (XSS-free).
- **Tailwind CSS**: Desain visual premium, responsif, dan elegan.
- **Chart.js**: Visualisasi data tren grafik garis interaktif.
- **Phosphor Icons**: Pustaka ikonografi modern dan konsisten.

---

## ⚙️ Petunjuk Instalasi dan Penggunaan

### 1. Prasyarat (Prerequisites)
Pastikan Anda telah menginstal **Python 3.10+** dan sistem database **PostgreSQL** (opsional, SQLite didukung secara bawaan/serverless).

### 2. Cara Clone Proyek
Buka terminal Anda dan jalankan perintah berikut untuk meng-clone repository proyek:
```bash
git clone https://github.com/nandaBlankon/Aceh-Sentimen-Analisis.git
cd Aceh-Sentimen-Analisis
```

### 3. Instalasi Dependensi Python
Instal seluruh modul pustaka yang dibutuhkan menggunakan `pip`:
```bash
pip install fastapi uvicorn requests beautifulsoup4 sqlalchemy pydantic-settings python-dotenv psycopg2-binary httpx google-generativeai
```

### 4. Konfigurasi File Environment (.env)
1. Salin berkas `.env` atau buat file baru bernama `.env` di root direktori proyek.
2. Tambahkan API Key Google Gemini Anda:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
DATABASE_URL=sqlite:///./aceh_sentimen.db
```
*(Catatan: Anda dapat mengganti `DATABASE_URL` ke PostgreSQL jika ingin menggunakan server database produksi).*

### 5. Inisialisasi Database
Jalankan skrip berikut untuk membuat tabel database serta mengisi data awal (*seed*):
```bash
# Membuat skema tabel
python3 init_db.py

# Memasukkan data awal (isu default)
python3 -c '
from app.database import SessionLocal
from app.models import Issue
db = SessionLocal()
if db.query(Issue).count() == 0:
    db.add(Issue(id=1, nama_isu="Dana Otsus Aceh", keyword="otsus", is_active=True))
    db.add(Issue(id=2, nama_isu="Infrastruktur & Jalan Rusak", keyword="jalan rusak", is_active=True))
    db.add(Issue(id=3, nama_isu="Pilkada Gubernur 2026", keyword="pilkada aceh", is_active=False))
    db.commit()
db.close()
'
```

### 6. Menjalankan Backend FastAPI
Jalankan server pengembangan Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Dokumentasi interaktif Swagger API akan tersedia di [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 7. Menjalankan Frontend Dasbor
Anda dapat membuka file `index.html` langsung di browser Anda, atau menyajikannya menggunakan HTTP server sederhana:
```bash
python3 -m http.server 3000 --bind 127.0.0.1
```
Buka peramban Anda dan akses **[http://127.0.0.1:3000/index.html](http://127.0.0.1:3000/index.html)**.

---

## 🔒 Catatan Keamanan (Security)
- **Zero Hardcoded Secrets**: Seluruh kunci rahasia (`GEMINI_API_KEY`) dimuat dari file `.env` di tingkat sistem dan tidak pernah disimpan dalam kode sumber.
- **SQL Injection Guard**: Seluruh parameter pencarian dienkapsulasi menggunakan parameter terikat yang aman lewat SQLAlchemy ORM.
- **XSS Mitigation**: Elemen teks data dari database disisipkan ke halaman web menggunakan properti aman `textContent` untuk meminimalkan risiko eksekusi skrip jahat secara tidak disengaja.
