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
    kategori_nama = serializers.CharField(source="kategori.nama_kategori", read_only=True)
    supplier_nama = serializers.CharField(source="supplier.nama_supplier", read_only=True)

    class Meta:
        model = Obat
        fields = "__all__"


class DetailTransaksiSerializer(serializers.ModelSerializer):
    # ✅ input harus bisa kirim id obat
    obat = serializers.PrimaryKeyRelatedField(queryset=Obat.objects.all())

    # ✅ output helper untuk frontend
    obat_nama = serializers.CharField(source="obat.nama_obat", read_only=True)
    harga_satuan = serializers.DecimalField(source="obat.harga", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetailTransaksi
        fields = "__all__"
        read_only_fields = ["subtotal"]

    def validate(self, attrs):
        obat = attrs.get("obat")
        jumlah = attrs.get("jumlah", 0)
        if obat and jumlah and obat.stok < jumlah:
            raise serializers.ValidationError({"jumlah": "Stok tidak cukup."})
        return attrs

    def create(self, validated_data):
        obat = validated_data["obat"]
        jumlah = validated_data["jumlah"]
        validated_data["subtotal"] = obat.harga * jumlah
        return super().create(validated_data)

    def update(self, instance, validated_data):
        obat = validated_data.get("obat", instance.obat)
        jumlah = validated_data.get("jumlah", instance.jumlah)
        if obat.stok < jumlah:
            raise serializers.ValidationError({"jumlah": "Stok tidak cukup."})
        instance.obat = obat
        instance.jumlah = jumlah
        instance.subtotal = obat.harga * jumlah
        instance.save()
        return instance


class TransaksiSerializer(serializers.ModelSerializer):
    detail = DetailTransaksiSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TransaksiPenjualan
        fields = "__all__"
        read_only_fields = ["user", "total_harga", "tanggal"]
