from django.contrib import admin
from django.db import transaction

from .models import (
    DetailTransaksi,
    KategoriObat,
    Obat,
    StockMovement,
    Supplier,
    TransaksiPenjualan,
)
from .services import record_adjustment


@admin.register(Obat)
class ObatAdmin(admin.ModelAdmin):
    list_display = ["nama_obat", "stok", "minimum_stock", "expiry_date"]
    search_fields = ["nama_obat"]

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        before = Obat.objects.select_for_update().get(pk=obj.pk).stok if change else 0
        super().save_model(request, obj, form, change)
        record_adjustment(obj, before, request.user, "Perubahan melalui admin")


class AuditReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Supplier)
admin.site.register(KategoriObat)
admin.site.register(TransaksiPenjualan, AuditReadOnlyAdmin)
admin.site.register(DetailTransaksi, AuditReadOnlyAdmin)
admin.site.register(StockMovement, AuditReadOnlyAdmin)
