# Aceh Sentimen Analisis (ASA)

Aceh Sentimen Analisis (ASA) adalah sistem pemantauan sentimen publik berbasis kecerdasan buatan (AI) yang mendeteksi dan menganalisis sentimen dari berbagai isu strategis di Provinsi Aceh. Sistem ini mengotomatisasi pengumpulan data dari portal berita lokal, menganalisis muatan sentimen menggunakan NLP (Natural Language Processing), dan menyajikan visualisasinya secara real-time pada dasbor interaktif.

Sistem dasbor dinamis ini memiliki SPA (Single Page Application) routing yang memuat data secara asinkron dari backend REST API FastAPI.

---

## 🚀 Fitur Utama

- **Web Scraping Berita Otomatis**: Mengunduh judul dan ringkasan berita secara dinamis berdasarkan kata kunci pencarian dari berbagai portal berita melalui integrasi Google News RSS (menggunakan HTTPX asinkron & BeautifulSoup). Proses scraping berjalan mulus di latar belakang (*background tasks*).
- **Klasifikasi Sentimen AI**: Menganalisis teks berita menggunakan Hugging Face Inference API dengan model IndoBERT (`indobenchmark/indobert-base-p2`) untuk memetakan sentimen menjadi **positif**, **negatif**, atau **netral**.
- **Dasbor Analitik Real-Time**:
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
- **Hugging Face Inference API**: Konektor model AI untuk klasifikasi sentimen teks bahasa Indonesia.
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
pip install fastapi uvicorn requests beautifulsoup4 sqlalchemy pydantic-settings python-dotenv psycopg2-binary httpx
```

### 4. Konfigurasi File Environment (.env)
1. Salin berkas `.env` atau buat file baru bernama `.env` di root direktori proyek.
2. Tambahkan token Hugging Face Anda (dapat dibuat gratis di [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)):
```env
HF_TOKEN=hf_xxxxxx_your_actual_token_here
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
python3 -m http.server 8080 --bind 127.0.0.1
```
Buka peramban Anda dan akses **[http://127.0.0.1:8080/index.html](http://127.0.0.1:8080/index.html)**.

---

## 🔒 Catatan Keamanan (Security)
- **Zero Hardcoded Secrets**: Seluruh kunci rahasia (`HF_TOKEN`) dimuat dari file `.env` di tingkat sistem dan tidak pernah disimpan dalam kode sumber.
- **SQL Injection Guard**: Seluruh parameter pencarian dienkapsulasi menggunakan parameter terikat yang aman lewat SQLAlchemy ORM.
- **XSS Mitigation**: Elemen teks data dari database disisipkan ke halaman web menggunakan properti aman `textContent` untuk meminimalkan risiko eksekusi skrip jahat secara tidak disengaja.
