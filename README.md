# 📦 Meditrack – Pharmacy Management System (Backend API)

Meditrack adalah **sistem backend berbasis Django REST Framework** yang dirancang untuk mendukung aplikasi **apotek online (e-commerce)** dengan arsitektur **decoupled**.  
Backend ini menyediakan REST API untuk autentikasi, manajemen data obat, serta transaksi penjualan berbasis keranjang (cart).

Project ini dikembangkan sebagai **Tugas Ujian Akhir Semester (UAS)** mata kuliah **Framework Programming dan Sistem Terdistribusi**.

---

## 🏗️ Arsitektur Sistem

Project ini menerapkan **Decoupled Architecture**, di mana:

- **Backend (Meditrack)**  
  Berperan sebagai penyedia data dan layanan API (JSON).
- **Frontend (PharmaCart)**  
  Berperan sebagai antarmuka pengguna (apotek online).

Semua komunikasi data dilakukan melalui **REST API**.

---

## 🚀 Fitur Utama

### 🔐 Autentikasi
- Register user
- Login menggunakan **Token Authentication**
- Proteksi endpoint dengan `IsAuthenticated`

### 💊 Manajemen Data
- CRUD Obat
- CRUD Kategori Obat
- CRUD Supplier

### 🛒 Transaksi & Cart (E-commerce Flow)
- Keranjang belanja (status `DRAFT`)
- Tambah / ubah / hapus item keranjang
- Checkout (status `PENDING`)
- Pembayaran (status `PAID`)
- Riwayat transaksi per user

### 📄 Dokumentasi API
- Swagger UI menggunakan **drf-spectacular**
- Endpoint dokumentasi:  
  ```
  /api/docs/
  ```

---

## 🧱 Teknologi yang Digunakan

- Python 3.11
- Django 4.x
- Django REST Framework
- Token Authentication
- drf-spectacular (Swagger)
- SQLite (development)

---

## 📂 Struktur Project

```
meditrack-pharmacy-management-system-django/
│
├── meditrack_project/        # Konfigurasi utama Django
├── meditrack/                # App utama (models, views, serializers)
├── db.sqlite3                # Database lokal (tidak di-track Git)
├── manage.py
└── requirements.txt
```

---

## 🔗 Endpoint Utama

### Auth
```
POST /api/auth/register/
POST /api/auth/token/
```

### Obat
```
GET    /api/obat/
POST   /api/obat/
PUT    /api/obat/{id}/
DELETE /api/obat/{id}/
```

### Cart & Transaksi
```
GET    /api/transaksi/cart/
POST   /api/transaksi/cart/add/
POST   /api/transaksi/cart/checkout/
POST   /api/transaksi/{id}/pay/
GET    /api/transaksi/my/
```

---

## ▶️ Cara Menjalankan Project

1. Clone repository
   ```bash
   git clone https://github.com/Freddy47588/meditrack-pharmacy-management-system-django.git
   cd meditrack-pharmacy-management-system-django
   ```

2. Aktifkan virtual environment
   ```bash
   python -m venv env
   env\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Konfigurasi environment (opsional untuk development)
   ```bash
   cp .env.example .env
   ```
   Di PowerShell gunakan `Copy-Item .env.example .env`. Isi
   `DJANGO_SECRET_KEY` dengan nilai pribadi yang dibuat menggunakan:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Simpan nilainya dalam tanda kutip di `.env`; jangan commit file tersebut.
   Tanpa key, development menggunakan key acak per proses sehingga session
   tidak bertahan setelah restart. Untuk deployment, wajib isi key, set
   `DJANGO_DEBUG=false`, dan atur `DJANGO_ALLOWED_HOSTS` (dipisahkan koma).
   Environment sistem memiliki prioritas terhadap `.env`.

5. Jalankan migrasi
   ```bash
   python manage.py migrate
   ```

6. Jalankan server
   ```bash
   python manage.py runserver
   ```

## Automated Testing

Prasyarat: Python 3.11, virtual environment aktif, dan dependency dari
`requirements.txt` terpasang (Django 4.2.7 / DRF 3.14.0). Tidak memerlukan
pytest, layanan eksternal, atau data development.

```bash
python manage.py check
python manage.py test
```

Tersedia **42 test** dalam `meditrack/tests/`: model dan constraint, CRUD API,
autentikasi token, isolasi transaksi pengguna, cart/checkout/pay, validasi form,
URL, Swagger UI, dan konfigurasi environment. Django membuat database SQLite
test di memori, menjalankan migrasi, lalu membersihkannya; `db.sqlite3` tidak
digunakan oleh test. Semua data test dibuat saat test berjalan.

Suite ini merupakan baseline, belum mencakup seluruh kasus konkurensi dan
masalah existing pada akses detail transaksi serta routing update item cart.

---

## 🎓 Catatan Akademik

- Project ini dibuat untuk **kepentingan akademik**
- Mengimplementasikan konsep:
  - REST API
  - Token Authentication
  - Relasi database
  - Sistem terdistribusi (frontend–backend terpisah)

---

## 👨‍💻 Author

**Fredi Irawan**  
Teknik Informatika  
Institut Asia Malang  
