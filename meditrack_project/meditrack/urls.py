from django.urls import path
from .views import (
    ObatListView, ObatDetailView, ObatCreateView, ObatUpdateView, ObatDeleteView,
    SupplierListView, SupplierDetailView, SupplierCreateView, SupplierUpdateView, SupplierDeleteView,
    KategoriListView, KategoriCreateView, KategoriUpdateView, KategoriDeleteView,
    TransaksiListView, TransaksiDetailView, TransaksiCreateView, TransaksiDeleteView,KasirView, HomeView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    
    path('obat/', ObatListView.as_view(), name='obat-list'),
    path('obat/<int:pk>/', ObatDetailView.as_view(), name='obat-detail'),
    path('obat/tambah/', ObatCreateView.as_view(), name='obat-tambah'),
    path('obat/<int:pk>/edit/', ObatUpdateView.as_view(), name='obat-edit'),
    path('obat/<int:pk>/hapus/', ObatDeleteView.as_view(), name='obat-hapus'),

    path('supplier/', SupplierListView.as_view(), name='supplier-list'),
    path('supplier/<int:pk>/', SupplierDetailView.as_view(), name='supplier-detail'),
    path('supplier/tambah/', SupplierCreateView.as_view(), name='supplier-tambah'),
    path('supplier/<int:pk>/edit/', SupplierUpdateView.as_view(), name='supplier-edit'),
    path('supplier/<int:pk>/hapus/', SupplierDeleteView.as_view(), name='supplier-hapus'),

    path('kategori/', KategoriListView.as_view(), name='kategori-list'),
    path('kategori/tambah/', KategoriCreateView.as_view(), name='kategori-tambah'),
    path('kategori/<int:pk>/edit/', KategoriUpdateView.as_view(), name='kategori-edit'),
    path('kategori/<int:pk>/hapus/', KategoriDeleteView.as_view(), name='kategori-hapus'),

    path('transaksi/', TransaksiListView.as_view(), name='transaksi-list'),
    path('transaksi/<int:pk>/', TransaksiDetailView.as_view(), name='transaksi-detail'),
    path('transaksi/tambah/', TransaksiCreateView.as_view(), name='transaksi-tambah'),
    path('transaksi/<int:pk>/hapus/', TransaksiDeleteView.as_view(), name='transaksi-hapus'),
    
    path('kasir/', KasirView, name='kasir'),
]