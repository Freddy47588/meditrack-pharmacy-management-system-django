from rest_framework import serializers
from .models import Obat, Supplier, KategoriObat, TransaksiPenjualan, DetailTransaksi


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = KategoriObat
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ObatSerializer(serializers.ModelSerializer):
    kategori = KategoriSerializer(read_only=True)
    supplier = SupplierSerializer(read_only=True)

    class Meta:
        model = Obat
        fields = "__all__"


class DetailTransaksiSerializer(serializers.ModelSerializer):
    obat = ObatSerializer(read_only=True)

    class Meta:
        model = DetailTransaksi
        fields = "__all__"


class TransaksiSerializer(serializers.ModelSerializer):
    detail = DetailTransaksiSerializer(many=True, read_only=True)

    class Meta:
        model = TransaksiPenjualan
        fields = "__all__"

