"""Create a standalone, repeatable demo dataset; never merge into existing data."""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from meditrack.models import (
    KategoriObat,
    Obat,
    StockMovement,
    Supplier,
    TransaksiPenjualan,
)
from meditrack.services import checkout, pay_transaction, restock, save_item


class Command(BaseCommand):
    help = "Seed an empty development database with demo inventory and sales (no default password)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Demo seed requires DJANGO_DEBUG=true. Production data is not modified."
            )
        User = get_user_model()
        demo = User.objects.filter(
            username="demo-pharmacist", email="demo@meditrack.invalid"
        ).first()
        if demo:
            self.stdout.write("Demo dataset already exists; no records changed.")
            return
        if any(
            model.objects.exists()
            for model in [User, KategoriObat, Supplier, Obat, TransaksiPenjualan]
        ):
            raise CommandError(
                "Database is not empty. Use a separate DJANGO_DB_PATH for demo data."
            )
        user = User.objects.create_user(
            "demo-pharmacist", email="demo@meditrack.invalid", is_staff=True
        )
        categories = [
            KategoriObat.objects.create(nama_kategori=name)
            for name in ["Analgesik", "Vitamin & Suplemen", "Perawatan Harian"]
        ]
        suppliers = [
            Supplier.objects.create(
                nama_supplier=name,
                alamat="Alamat fiktif untuk demonstrasi",
                no_telepon="0000000000",
            )
            for name in ["Sehat Sentosa Demo", "Medika Nusantara Demo"]
        ]
        today = timezone.localdate()
        products = []
        for i, (name, price, stock, expiry) in enumerate(
            [
                ("Paracetamol 500 mg", "12000", 120, 365),
                ("Vitamin C 500 mg", "24000", 85, 180),
                ("Oralit Sachet", "4500", 50, 90),
                ("Antiseptik 60 ml", "18000", 30, 20),
                ("Vitamin B Kompleks", "16000", 4, 120),
                ("Kasa Steril", "8000", 0, 365),
                ("Saline 100 ml", "15000", 12, -5),
                ("Multivitamin Tablet", "32000", 8, 10),
                ("Plester Luka", "7000", 36, 500),
                ("Vitamin D3", "28000", 18, 30),
                ("Kapas Medis", "9500", 24, 720),
                ("Zinc Tablet", "14000", 20, 200),
                ("Masker Medis", "22000", 40, 365),
                ("Hand Sanitizer", "17000", 15, 180),
            ]
        ):
            obat = Obat.objects.create(
                nama_obat=name,
                kategori=categories[0 if i == 0 else 1 if i in (1, 4, 7, 9, 11) else 2],
                supplier=suppliers[i % 2],
                harga=Decimal(price),
                stok=0,
                minimum_stock=5 if i % 2 == 0 else 10,
                expiry_date=today + timedelta(days=expiry),
            )
            if stock:
                restock(obat.pk, stock, user, "Persediaan awal demo")
            products.append(obat)
        for days in range(6, -1, -1):
            trx = TransaksiPenjualan.objects.create(user=user)
            save_item(trx, products[0], 2 + days % 3)
            save_item(trx, products[1], 1 + days % 2)
            checkout(trx.pk, user)
            pay_transaction(trx.pk, user)
            stamp = timezone.now() - timedelta(days=days)
            TransaksiPenjualan.objects.filter(pk=trx.pk).update(tanggal=stamp)
            StockMovement.objects.filter(reference=f"transaksi:{trx.pk}").update(
                timestamp=stamp
            )
        pending = TransaksiPenjualan.objects.create(user=user)
        save_item(pending, products[2], 2)
        checkout(pending.pk, user)
        self.stdout.write(
            self.style.SUCCESS(
                "Demo created: 3 categories, 2 suppliers, 14 medicines, 8 transactions."
            )
        )
        self.stdout.write(
            "Set a private login password with: python manage.py changepassword demo-pharmacist"
        )
