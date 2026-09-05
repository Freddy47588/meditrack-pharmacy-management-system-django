from django import forms
from .models import Obat, Supplier, KategoriObat, DetailTransaksi


class ObatForm(forms.ModelForm):
    minimum_stock = forms.IntegerField(min_value=0, required=False, initial=5)

    def clean_minimum_stock(self):
        value = self.cleaned_data.get('minimum_stock')
        return 5 if value is None else value

    class Meta:
        model = Obat
        fields = ["nama_obat", "kategori", "supplier", "harga", "stok", "minimum_stock", "expiry_date"]
        widgets = {"expiry_date": forms.DateInput(attrs={"type": "date"})}


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


class RestockForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=2147483647, label='Jumlah restock')
    note = forms.CharField(required=False, max_length=1000, widget=forms.Textarea(attrs={'rows': 3}), label='Catatan')
