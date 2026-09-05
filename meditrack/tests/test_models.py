from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from meditrack.models import DetailTransaksi, KategoriObat, Obat, Supplier, TransaksiPenjualan


class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='model-user')
        cls.kategori = KategoriObat.objects.create(nama_kategori='Analgesik')
        cls.supplier = Supplier.objects.create(
            nama_supplier='Supplier Test', alamat='Jalan Test', no_telepon='021123456'
        )
        cls.obat = Obat.objects.create(
            nama_obat='Paracetamol', kategori=cls.kategori, supplier=cls.supplier,
            harga=Decimal('12500.50'), stok=10,
        )
        cls.transaksi = TransaksiPenjualan.objects.create(user=cls.user)
        cls.detail = DetailTransaksi.objects.create(
            transaksi=cls.transaksi, obat=cls.obat, jumlah=2, subtotal=Decimal('25001.00')
        )

    def test_catalog_fields_and_string_representations(self):
        self.kategori.refresh_from_db()
        self.supplier.refresh_from_db()
        self.obat.refresh_from_db()
        self.assertEqual(str(self.kategori), 'Analgesik')
        self.assertEqual(str(self.supplier), 'Supplier Test')
        self.assertEqual(self.supplier.alamat, 'Jalan Test')
        self.assertEqual(self.supplier.no_telepon, '021123456')
        self.assertEqual(str(self.obat), 'Paracetamol')
        self.assertEqual(self.obat.harga, Decimal('12500.50'))
        self.assertEqual(self.obat.stok, 10)
        self.assertTrue(timezone.is_aware(self.obat.tanggal_masuk))

    def test_transaction_defaults_and_string(self):
        self.transaksi.refresh_from_db()
        self.assertEqual(self.transaksi.status, 'DRAFT')
        self.assertEqual(self.transaksi.total_harga, Decimal('0.00'))
        self.assertTrue(timezone.is_aware(self.transaksi.tanggal))
        self.assertEqual(str(self.transaksi), f'Transaksi #{self.transaksi.pk} - model-user - DRAFT')

    def test_detail_fields_and_relationships(self):
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.jumlah, 2)
        self.assertEqual(self.detail.subtotal, Decimal('25001.00'))
        self.assertEqual(str(self.detail), 'Paracetamol x 2')
        self.assertEqual(self.obat.kategori, self.kategori)
        self.assertEqual(self.obat.supplier, self.supplier)
        self.assertEqual(self.detail.obat, self.obat)
        self.assertEqual(self.detail.transaksi, self.transaksi)
        self.assertEqual(self.transaksi.user, self.user)
        self.assertEqual(self.kategori.obat.get(), self.obat)
        self.assertEqual(self.supplier.obat_supplier.get(), self.obat)
        self.assertEqual(self.transaksi.detail.get(), self.detail)
        self.assertEqual(self.obat.detail_transaksi.get(), self.detail)
        self.assertEqual(self.user.transaksi_penjualan.get(), self.transaksi)

    def test_database_rejects_negative_stock(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Obat.objects.filter(pk=self.obat.pk).update(stok=-1)

    def test_database_rejects_negative_quantity(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DetailTransaksi.objects.filter(pk=self.detail.pk).update(jumlah=-1)

    def test_transaction_requires_user(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TransaksiPenjualan.objects.create()

    def test_deleting_transaction_cascades_details_but_preserves_catalog(self):
        self.transaksi.delete()
        self.assertFalse(DetailTransaksi.objects.exists())
        self.assertTrue(Obat.objects.filter(pk=self.obat.pk).exists())
