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
├── db.sqlite3
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

4. Jalankan migrasi
   ```bash
   python manage.py migrate
   ```

5. Jalankan server
   ```bash
   python manage.py runserver
   ```

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
