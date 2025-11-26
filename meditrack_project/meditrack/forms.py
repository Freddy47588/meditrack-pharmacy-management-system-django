from django import forms
from .models import Obat, Supplier, KategoriObat, TransaksiPenjualan


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


class TransaksiForm(forms.ModelForm):
    class Meta:
        model = TransaksiPenjualan
        fields = ["total_harga"]


# ===========================
# F O R M   K A S I R
# ===========================

# forms.py
from django import forms
from .models import Obat, DetailTransaksi

class KasirItemForm(forms.ModelForm):
    class Meta:
        model = DetailTransaksi
        fields = ['obat', 'jumlah']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        obat_queryset = Obat.objects.all()

        # Custom select widget
        choices = []
        for obat in obat_queryset:
            label = f"{obat.nama_obat} — Stok: {obat.stok}"

            if obat.stok == 0:
                # disable jika stok habis
                choices.append((
                    obat.id,
                    {'label': label, 'disabled': True}
                ))
            else:
                choices.append((obat.id, label))

        self.fields['obat'].choices = [
            (o.id, f"{o.nama_obat} — Stok: {o.stok}") for o in obat_queryset
        ]

        # Override dengan menambahkan atribut "disabled" via JS nanti
        self.fields['obat'].widget.attrs.update({
            'class': 'w-full border rounded-lg px-3 py-2',
        })

