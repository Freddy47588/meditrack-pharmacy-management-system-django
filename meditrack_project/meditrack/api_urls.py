# meditrack/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ObatViewSet,
    SupplierViewSet,
    KategoriViewSet,
    TransaksiViewSet,
    DetailTransaksiViewSet,
)

# Router untuk endpoint otomatis / CRUD API
router = DefaultRouter()
router.register(r'obat', ObatViewSet, basename='obat')
router.register(r'supplier', SupplierViewSet, basename='supplier')
router.register(r'kategori', KategoriViewSet, basename='kategori')
router.register(r'transaksi', TransaksiViewSet, basename='transaksi')
router.register(r'detail-transaksi', DetailTransaksiViewSet, basename='detail-transaksi')

urlpatterns = [
    # API utama
    path('', include(router.urls)),
]
