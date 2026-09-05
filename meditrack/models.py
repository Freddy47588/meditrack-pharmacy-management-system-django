from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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
        KategoriObat, on_delete=models.PROTECT, related_name="obat"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="obat_supplier"
    )
    harga = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    stok = models.PositiveIntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    minimum_stock = models.PositiveIntegerField(default=5)
    tanggal_masuk = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(harga__gte=0), name="obat_nonnegative_price"
            )
        ]
        verbose_name = "Obat"
        verbose_name_plural = "Obat"

    @property
    def stock_status(self):
        if self.stok == 0:
            return "empty"
        return "low" if self.stok <= self.minimum_stock else "safe"

    @property
    def expiry_status(self):
        if not self.expiry_date:
            return "unknown"
        today = timezone.localdate()
        if self.expiry_date < today:
            return "expired"
        return (
            "near_expiry" if self.expiry_date <= today + timedelta(days=30) else "safe"
        )

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
        related_name="transaksi_penjualan",
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
        TransaksiPenjualan, on_delete=models.CASCADE, related_name="detail"
    )
    obat = models.ForeignKey(
        Obat, on_delete=models.PROTECT, related_name="detail_transaksi"
    )
    jumlah = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(jumlah__gt=0), name="detail_positive_quantity"
            )
        ]
        verbose_name = "Detail Transaksi"
        verbose_name_plural = "Detail Transaksi"

    @property
    def unit_price(self):
        return self.subtotal / self.jumlah if self.jumlah else 0

    def __str__(self):
        return f"{self.obat.nama_obat} x {self.jumlah}"


class StockMovement(models.Model):
    TYPES = [
        ("IN", "Restock"),
        ("SALE", "Penjualan"),
        ("ADJUSTMENT", "Penyesuaian"),
        ("RETURN", "Pengembalian"),
    ]
    obat = models.ForeignKey(
        Obat, on_delete=models.PROTECT, related_name="stock_movements"
    )
    tipe = models.CharField(max_length=12, choices=TYPES)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    reference = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp", "-pk"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0), name="movement_positive_quantity"
            )
        ]

    def __str__(self):
        return f"{self.obat} / {self.tipe} / {self.quantity}"
