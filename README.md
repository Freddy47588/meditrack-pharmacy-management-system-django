# MediTrack

Backend manajemen apotek berbasis Django REST Framework untuk mengelola obat,
kategori, supplier, dan transaksi penjualan melalui keranjang belanja.
Proyek ini memperlihatkan pemodelan relasi database, autentikasi token, REST API,
dan automated testing dalam satu aplikasi Django.

MediTrack dikembangkan sebagai tugas UAS **Framework Programming dan Sistem
Terdistribusi**, dengan API yang ditujukan untuk frontend terpisah **PharmaCart**.
Frontend tersebut tidak disertakan dalam repository ini. Repository juga memuat
dashboard dan halaman manajemen HTML dari implementasi awal.

Proyek ini merupakan portfolio akademik; lihat [Known Limitations](#known-limitations)
untuk batasan implementasi yang masih perlu ditangani sebelum deployment publik.

## Features

- Registrasi akun dan login menggunakan token Django REST Framework.
- CRUD obat, kategori obat, dan supplier; katalog dapat dibaca tanpa login.
- Pencarian obat berdasarkan nama, kategori, atau supplier serta pengurutan
  berdasarkan nama, harga, stok, atau tanggal masuk.
- Keranjang berstatus `DRAFT`, penambahan dan penghapusan item, serta perhitungan
  subtotal dan total harga.
- Checkout mengubah status menjadi `PENDING` dan mengurangi stok; action `pay`
  menandai transaksi sebagai `PAID`. Ini adalah simulasi status pembayaran,
  belum terintegrasi payment gateway.
- Daftar transaksi milik pengguna dan riwayat pesanan selain `DRAFT`.
- Dashboard HTML dengan jumlah obat, supplier, kategori, transaksi, dan daftar
  obat dengan stok paling banyak lima; Django admin untuk kelima model.
- Dokumentasi Swagger/OpenAPI dan 42 automated tests.

## Tech Stack

| Komponen | Implementasi |
| --- | --- |
| Runtime | Python 3.11 |
| Web framework | Django 4.2.7 |
| REST API | Django REST Framework 3.14.0, TokenAuthentication |
| Database | SQLite |
| API documentation | drf-spectacular 0.27.1 / Swagger UI |
| Environment configuration | python-dotenv 1.0.0 |
| HTML UI | Django templates, Tailwind CSS melalui CDN |
| Testing | Django test runner dan DRF APITestCase |

Versi dependency tercantum dalam [requirements.txt](requirements.txt).
`django-filter` dan `django-cors-headers` tercantum sebagai dependency, tetapi
belum diaktifkan pada konfigurasi aplikasi. Search dan ordering menggunakan
filter bawaan DRF.

## Project Structure

```text
meditrack-pharmacy-management-system-django/
├── meditrack/
│   ├── models.py             # Kategori, supplier, obat, transaksi, detail
│   ├── serializers.py        # Representasi dan validasi API
│   ├── views.py              # Viewset API dan view HTML legacy
│   ├── auth_api.py           # Registrasi pengguna
│   ├── api_urls.py           # Router API
│   ├── urls.py               # URL HTML
│   ├── forms.py
│   ├── migrations/
│   ├── templates/
│   └── tests/                # Model, API, form, URL, settings
├── meditrack_project/        # Settings dan URL utama Django
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

## Installation

Prasyarat: Git dan Python 3.11 beserta pip. Jalankan perintah berikut dari terminal.

### 1. Clone repository

```bash
git clone https://github.com/Freddy47588/meditrack-pharmacy-management-system-django.git
cd meditrack-pharmacy-management-system-django
python -m venv .venv
```

### 2. Aktifkan virtual environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependency dan siapkan environment

```bash
python -m pip install -r requirements.txt
```

Salin contoh konfigurasi dengan `Copy-Item .env.example .env` di PowerShell,
`copy .env.example .env` di Command Prompt, atau `cp .env.example .env` di
macOS/Linux. Isi key pribadi menggunakan output perintah berikut:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Simpan output dalam tanda kutip pada `DJANGO_SECRET_KEY` di `.env`; jangan commit
key atau file `.env`. Lihat [Environment Variables](#environment-variables)
untuk perilaku default.

### 4. Siapkan database dan jalankan server

```bash
python manage.py migrate
python manage.py check
python manage.py runserver
```

Buka dashboard di <http://127.0.0.1:8000/> atau Swagger UI di
<http://127.0.0.1:8000/api/docs/>. Database hasil migrasi awal belum berisi data
aplikasi. Untuk mengisi data lewat `/admin/`, buat akun admin terlebih dahulu:

```bash
python manage.py createsuperuser
```

## Running Tests

Dengan virtual environment aktif dan dependency terpasang, jalankan dari root:

```bash
python manage.py check
python manage.py test
```

Tersedia **42 test**: 7 model, 25 API, 2 form, 5 URL/Swagger, dan 3 konfigurasi.
Cakupannya mencakup CRUD, relasi dan constraint, register/login, permission,
isolasi transaksi per pengguna, perhitungan subtotal, validasi stok,
checkout, pembayaran, dan riwayat pesanan.

Django membuat database SQLite test **di memori**, menjalankan migrasi, dan
membersihkannya setelah pengujian. Semua data dibuat saat test berjalan;
`db.sqlite3`, server development, dan layanan eksternal tidak diperlukan.
Suite ini adalah baseline dan belum mencakup semua masalah pada
[Known Limitations](#known-limitations).

## API Documentation

- Swagger UI: <http://127.0.0.1:8000/api/docs/>
- OpenAPI schema: <http://127.0.0.1:8000/api/schema/>

Kedua route dokumentasi dapat diakses tanpa login. Swagger UI memuat aset dari
CDN sehingga tampilan interaktifnya memerlukan koneksi internet. Schema otomatis
belum mendeskripsikan seluruh custom action secara akurat; lihat batasan di bawah.

Untuk request terproteksi, register melalui `/api/auth/register/` dengan field
`username`, `password`, dan `password2`, lalu login melalui `/api/auth/token/`
dengan `username` dan `password`. Gunakan nilai `token` dari respons login pada
header berikut; placeholder ini bukan token aktif:

```http
Authorization: Token <your-token>
```

## API Overview

Semua path menggunakan trailing slash. `{id}` dan `{item_id}` adalah ID record.

| Method | Endpoint | Fungsi / akses |
| --- | --- | --- |
| POST | `/api/auth/register/` | Membuat akun; publik |
| POST | `/api/auth/token/` | Mendapatkan token dari kredensial login; publik |
| GET, POST | `/api/obat/` | Daftar / buat obat |
| GET, PUT, PATCH, DELETE | `/api/obat/{id}/` | Detail / ubah / hapus obat |
| GET, POST | `/api/kategori/`, `/api/supplier/` | Daftar / buat kategori atau supplier |
| GET, PUT, PATCH, DELETE | `/api/kategori/{id}/`, `/api/supplier/{id}/` | Detail / ubah / hapus kategori atau supplier |
| GET, POST | `/api/transaksi/` | Daftar transaksi sendiri / buat transaksi; login |
| GET, PUT, PATCH, DELETE | `/api/transaksi/{id}/` | Detail / ubah / hapus transaksi sendiri; login |
| GET | `/api/transaksi/cart/` | Ambil atau buat keranjang `DRAFT`; login |
| POST | `/api/transaksi/cart/add/` | Tambah item dengan `obat` dan `jumlah`; login |
| DELETE | `/api/transaksi/cart/items/{item_id}/` | Hapus item keranjang sendiri; login |
| POST | `/api/transaksi/cart/checkout/` | Checkout keranjang; login |
| POST | `/api/transaksi/{id}/pay/` | Tandai transaksi `PENDING` sebagai `PAID`; login |
| GET | `/api/transaksi/my/` | Riwayat transaksi sendiri selain `DRAFT`; login |
| GET, POST | `/api/detail-transaksi/` | Daftar / buat detail; login, lihat batasan kepemilikan |
| GET, PUT, PATCH, DELETE | `/api/detail-transaksi/{id}/` | Detail / ubah / hapus item; login, lihat batasan kepemilikan |

Pembacaan obat, kategori, dan supplier bersifat publik; penulisannya memerlukan
login, tetapi belum dibatasi khusus untuk staff. Contoh pencarian dan pengurutan:
`GET /api/obat/?search=paracetamol&ordering=harga`.

## Screenshots

Screenshot akan ditambahkan pada pembaruan berikutnya. Halaman yang disarankan:

- `/api/docs/`: daftar endpoint dan contoh respons katalog.
- `/`: dashboard dengan ringkasan data dan indikator stok rendah.
- `/obat/`: daftar obat dengan kategori, harga, dan stok.

Gunakan aplikasi yang benar-benar berjalan dengan data demo dan sembunyikan
token atau data pribadi sebelum menyimpan screenshot.

## Database

Database SQLite lokal `db.sqlite3` tidak disimpan dalam version control.
Jalankan migrasi setelah clone; file database development dibuat saat migrasi.
Migration files tetap disertakan dalam repository.

Model utama: `KategoriObat` dan `Supplier` berelasi dengan `Obat`;
`TransaksiPenjualan` dimiliki pengguna dan memiliki banyak `DetailTransaksi`
yang merujuk ke obat. Harga, subtotal, dan total menggunakan `DecimalField`.

## Environment Variables

Konfigurasi dimuat dari `.env` di root menggunakan python-dotenv. Environment
sistem memiliki prioritas terhadap file tersebut. Lihat [.env.example](.env.example).

| Variabel | Default tanpa konfigurasi | Keterangan |
| --- | --- | --- |
| `DJANGO_DEBUG` | `true` | Nilai `true`, `1`, `yes`, atau `on` mengaktifkan debug; gunakan `false` untuk deployment |
| `DJANGO_SECRET_KEY` | Key acak per proses saat debug aktif | Isi key pribadi agar session bertahan setelah restart; wajib ketika debug dimatikan |
| `DJANGO_ALLOWED_HOSTS` | Daftar kosong | Host dipisahkan koma; `.env.example` menyediakan `localhost,127.0.0.1` |

Tanpa key dan dengan `DJANGO_DEBUG=false`, aplikasi menolak startup.
Pengaturan ini belum merupakan konfigurasi deployment produksi yang lengkap.

## Known Limitations

- **Otorisasi:** CRUD detail transaksi belum memfilter pemilik; akun terautentikasi
  dapat mengakses detail pengguna lain. View HTML legacy belum memiliki pembatasan
  akses, dan CRUD katalog belum membedakan peran pembeli dan pengelola.
- **Integritas transaksi:** perubahan detail lewat CRUD tidak menghitung ulang
  total transaksi. Status dapat diubah lewat CRUD sehingga melewati checkout/pay.
  Checkout multi-item dapat menyimpan pengurangan stok parsial saat item berikutnya
  gagal; konsistensi stok pada request bersamaan juga belum dijamin.
- **Routing cart:** action PATCH dan DELETE item memakai path yang sama pada dua
  route terpisah. PATCH `/api/transaksi/cart/items/{item_id}/` tertutup oleh route
  DELETE dan belum dapat digunakan sebagaimana dimaksud.
- **HTML legacy:** template kasir dan form tambah transaksi belum tersedia;
  pembuatan transaksi pada alur tersebut belum mengisi pengguna yang diwajibkan model.
- **OpenAPI:** introspeksi otomatis belum lengkap untuk registrasi dan beberapa
  action cart/pay; schema bukan jaminan seluruh request/response action akurat.

## License

Repository belum memiliki file lisensi. Pemilik proyek perlu menentukan lisensi
sebelum menambahkan ketentuan penggunaan atau badge lisensi.

## Author

**Fredi Irawan**  
Teknik Informatika — Institut Asia Malang
