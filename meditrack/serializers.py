from rest_framework import serializers

from .models import DetailTransaksi, KategoriObat, Obat, Supplier, TransaksiPenjualan


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = KategoriObat
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ObatSerializer(serializers.ModelSerializer):
    stock_status = serializers.CharField(read_only=True)
    expiry_status = serializers.CharField(read_only=True)
    stok = serializers.IntegerField(min_value=0, max_value=2147483647)
    kategori_nama = serializers.CharField(
        source="kategori.nama_kategori", read_only=True
    )
    supplier_nama = serializers.CharField(
        source="supplier.nama_supplier", read_only=True
    )

    class Meta:
        model = Obat
        fields = "__all__"


class DetailTransaksiSerializer(serializers.ModelSerializer):
    jumlah = serializers.IntegerField(min_value=1)
    obat = serializers.PrimaryKeyRelatedField(queryset=Obat.objects.all())

    obat_nama = serializers.CharField(source="obat.nama_obat", read_only=True)
    harga_satuan = serializers.DecimalField(
        source="unit_price", max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = DetailTransaksi
        fields = "__all__"
        read_only_fields = ["subtotal"]

    def validate(self, attrs):
        trx = attrs.get("transaksi", getattr(self.instance, "transaksi", None))
        request = self.context.get("request")
        if trx and request and trx.user_id != request.user.pk:
            raise serializers.ValidationError(
                {"transaksi": "Transaksi tidak tersedia."}
            )
        if self.instance and trx.pk != self.instance.transaksi_id:
            raise serializers.ValidationError(
                {"transaksi": "Transaksi item tidak dapat dipindahkan."}
            )
        if trx and trx.status != "DRAFT":
            raise serializers.ValidationError("Hanya transaksi DRAFT dapat diubah.")
        obat = attrs.get("obat")
        jumlah = attrs.get("jumlah", 0)
        if obat and jumlah and obat.stok < jumlah:
            raise serializers.ValidationError({"jumlah": "Stok tidak cukup."})
        return attrs


class TransaksiSerializer(serializers.ModelSerializer):
    detail = DetailTransaksiSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TransaksiPenjualan
        fields = "__all__"
        read_only_fields = ["user", "total_harga", "tanggal", "status"]


class CartAddSerializer(serializers.Serializer):
    obat = serializers.PrimaryKeyRelatedField(queryset=Obat.objects.all())
    jumlah = serializers.IntegerField(min_value=1)


class CartUpdateSerializer(serializers.Serializer):
    obat = serializers.PrimaryKeyRelatedField(
        queryset=Obat.objects.all(), required=False
    )
    jumlah = serializers.IntegerField(min_value=1, required=False)
