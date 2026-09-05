from django.contrib import admin
from .models import Obat, Supplier, KategoriObat, TransaksiPenjualan, DetailTransaksi

admin.site.register(Obat)
admin.site.register(Supplier)
admin.site.register(KategoriObat)
admin.site.register(TransaksiPenjualan)
admin.site.register(DetailTransaksi)
