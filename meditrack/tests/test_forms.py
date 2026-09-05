from django.test import TestCase

from meditrack.forms import KategoriForm, ObatForm, SupplierForm
from meditrack.models import KategoriObat, Supplier


class FormTests(TestCase):
    def test_catalog_forms_require_fields(self):
        for form_class, fields in [
            (KategoriForm, ['nama_kategori']),
            (SupplierForm, ['nama_supplier', 'alamat', 'no_telepon']),
            (ObatForm, ['nama_obat', 'kategori', 'supplier', 'harga', 'stok']),
        ]:
            with self.subTest(form=form_class.__name__):
                form = form_class(data={})
                self.assertFalse(form.is_valid())
                self.assertEqual(set(form.errors), set(fields))

    def test_obat_form_saves_valid_data_and_rejects_negative_stock(self):
        kategori = KategoriObat.objects.create(nama_kategori='Vitamin')
        supplier = Supplier.objects.create(nama_supplier='Test', alamat='Test', no_telepon='123')
        data = {'nama_obat': 'Vitamin C', 'kategori': kategori.pk,
                'supplier': supplier.pk, 'harga': '1000.50', 'stok': 4}
        form = ObatForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        obat = form.save()
        obat.refresh_from_db()
        self.assertEqual(obat.stok, 4)
        self.assertEqual(obat.kategori, kategori)
        form = ObatForm(data={**data, 'stok': -1})
        self.assertFalse(form.is_valid())
        self.assertIn('stok', form.errors)
