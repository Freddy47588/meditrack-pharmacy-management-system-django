from django.conf import settings
from django.db import models


# ================================
# 1. Kategori Obat
# ================================
class KategoriObat(models.Model):
    nama_kategori = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Kategori Obat"
        verbose_name_plural = "Kategori Obat"

    def __str__(self):
        return self.nama_kategori


# ================================
# 2. Supplier
# ================================
class Supplier(models.Model):
    nama_supplier = models.CharField(max_length=100)
    alamat = models.TextField()
    no_telepon = models.CharField(max_length=15)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Supplier"

    def __str__(self):
        return self.nama_supplier


# ================================
# 3. Obat
# ================================
class Obat(models.Model):
    nama_obat = models.CharField(max_length=150)
    kategori = models.ForeignKey(
        KategoriObat,
        on_delete=models.CASCADE,
        related_name="obat"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="obat_supplier"
    )
    harga = models.DecimalField(max_digits=12, decimal_places=2)
    stok = models.PositiveIntegerField()
    tanggal_masuk = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Obat"
        verbose_name_plural = "Obat"

    def __str__(self):
        return self.nama_obat


# ================================
# 4. Transaksi Penjualan
# ================================
class TransaksiPenjualan(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "Keranjang (Draft)"),
        ("PENDING", "Menunggu Pembayaran"),
        ("PAID", "Lunas"),
        ("CANCELLED", "Dibatalkan"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transaksi_penjualan"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="DRAFT")
    tanggal = models.DateTimeField(auto_now_add=True)
    total_harga = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Transaksi #{self.id} - {self.user} - {self.status}"

# ================================
# 5. Detail Transaksi
# ================================
class DetailTransaksi(models.Model):
    transaksi = models.ForeignKey(
        TransaksiPenjualan,
        on_delete=models.CASCADE,
        related_name="detail"
    )
    obat = models.ForeignKey(
        Obat,
        on_delete=models.CASCADE,
        related_name="detail_transaksi"
    )
    jumlah = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Detail Transaksi"
        verbose_name_plural = "Detail Transaksi"

    def __str__(self):
        return f"{self.obat.nama_obat} x {self.jumlah}"
