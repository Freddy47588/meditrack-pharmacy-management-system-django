from django import forms
from .models import Obat, Supplier, KategoriObat, DetailTransaksi


class ObatForm(forms.ModelForm):
    class Meta:
        model = Obat
        fields = ["nama_obat", "kategori", "supplier", "harga", "stok"]


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["nama_supplier", "alamat", "no_telepon"]


class KategoriForm(forms.ModelForm):
    class Meta:
        model = KategoriObat
        fields = ["nama_kategori"]


class KasirItemForm(forms.ModelForm):
    jumlah = forms.IntegerField(min_value=1)

    class Meta:
        model = DetailTransaksi
        fields = ['obat', 'jumlah']
