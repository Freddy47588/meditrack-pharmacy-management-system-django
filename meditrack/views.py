from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from .services import get_cart, owned_draft, save_item, recalc, checkout, pay_transaction
from .permissions import StaffOrReadOnly

class StaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

class OwnedMixin(LoginRequiredMixin):
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.views import View
from django.urls import reverse_lazy
from django.forms import formset_factory
from rest_framework import  viewsets
from django.contrib import messages

from .models import (
    Obat, Supplier, KategoriObat,
    TransaksiPenjualan, DetailTransaksi
)
from .forms import (
    ObatForm, SupplierForm, KategoriForm,
    KasirItemForm
)
from .serializers import (
    ObatSerializer, SupplierSerializer, KategoriSerializer,
    TransaksiSerializer, DetailTransaksiSerializer
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction
from django.db.models import Sum


# =====================================================
# HOME DASHBOARD
# =====================================================

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            "total_obat": Obat.objects.count(),
            "total_supplier": Supplier.objects.count(),
            "total_kategori": KategoriObat.objects.count(),
            "total_transaksi": TransaksiPenjualan.objects.filter(user=request.user).count(),
            "obat_stok_rendah": Obat.objects.filter(stok__lte=5),
        }
        return render(request, "meditrack/home.html", context)


# =====================================================
# O B A T
# =====================================================

class ObatListView(ListView):
    model = Obat
    template_name = "meditrack/obat_list.html"
    context_object_name = "obat_list"


class ObatDetailView(DetailView):
    model = Obat
    template_name = "meditrack/obat_detail.html"


class ObatCreateView(StaffMixin, CreateView):
    model = Obat
    form_class = ObatForm
    template_name = "meditrack/obat_form.html"
    success_url = reverse_lazy("obat-list")

    def form_valid(self, form):
        messages.success(self.request, "Obat berhasil ditambahkan!")
        return super().form_valid(form)


class ObatUpdateView(StaffMixin, UpdateView):
    model = Obat
    form_class = ObatForm
    template_name = "meditrack/obat_form.html"
    success_url = reverse_lazy("obat-list")
    
    def form_valid(self, form):
        messages.success(self.request, "Obat berhasil diperbarui!")
        return super().form_valid(form)

    


class ObatDeleteView(StaffMixin, DeleteView):
    model = Obat
    template_name = "meditrack/obat_confirm_delete.html"
    success_url = reverse_lazy("obat-list")


# =====================================================
# S U P P L I E R
# =====================================================

class SupplierListView(ListView):
    model = Supplier
    template_name = "meditrack/supplier_list.html"
    context_object_name = "supplier_list"


class SupplierDetailView(DetailView):
    model = Supplier
    template_name = "meditrack/supplier_detail.html"


from django.contrib import messages

class SupplierCreateView(StaffMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "meditrack/supplier_form.html"
    success_url = reverse_lazy("supplier-list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier berhasil ditambahkan!")
        return super().form_valid(form)


class SupplierUpdateView(StaffMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "meditrack/supplier_form.html"
    success_url = reverse_lazy("supplier-list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier berhasil diperbarui!")
        return super().form_valid(form)



class SupplierDeleteView(StaffMixin, DeleteView):
    model = Supplier
    template_name = "meditrack/supplier_confirm_delete.html"
    success_url = reverse_lazy("supplier-list")


# =====================================================
# K A T E G O R I
# =====================================================

class KategoriListView(ListView):
    model = KategoriObat
    template_name = "meditrack/kategori_list.html"
    context_object_name = "kategori_list"


from django.contrib import messages

class KategoriCreateView(StaffMixin, CreateView):
    model = KategoriObat
    form_class = KategoriForm
    template_name = "meditrack/kategori_form.html"
    success_url = reverse_lazy("kategori-list")

    def form_valid(self, form):
        messages.success(self.request, "Kategori berhasil ditambahkan!")
        return super().form_valid(form)


class KategoriUpdateView(StaffMixin, UpdateView):
    model = KategoriObat
    form_class = KategoriForm
    template_name = "meditrack/kategori_form.html"
    success_url = reverse_lazy("kategori-list")

    def form_valid(self, form):
        messages.success(self.request, "Kategori berhasil diperbarui!")
        return super().form_valid(form)


class KategoriDeleteView(StaffMixin, DeleteView):
    model = KategoriObat
    template_name = "meditrack/kategori_confirm_delete.html"
    success_url = reverse_lazy("kategori-list")


# =====================================================
# T R A N S A K S I
# =====================================================

class TransaksiListView(OwnedMixin, ListView):
    model = TransaksiPenjualan
    template_name = "meditrack/transaksi_list.html"
    context_object_name = "transaksi_list"


class TransaksiDetailView(OwnedMixin, DetailView):
    model = TransaksiPenjualan
    template_name = "meditrack/transaksi_detail.html"


class TransaksiCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect('kasir')

    post = get


# =====================================================
# K A S I R  ( F O R M S E T )
# =====================================================

@login_required
def KasirView(request):
    if not request.user.is_staff:
        raise PermissionDenied
    KasirFormSet = formset_factory(KasirItemForm, extra=3, min_num=1, validate_min=True)
    formset = KasirFormSet(request.POST or None)
    if request.method == "POST" and formset.is_valid():
        try:
            with transaction.atomic():
                trx = TransaksiPenjualan.objects.create(user=request.user)
                for row in formset.cleaned_data:
                    if row:
                        save_item(trx, row['obat'], row['jumlah'])
                trx = checkout(trx.pk, request.user)
            messages.success(request, "Checkout berhasil. Transaksi menunggu pembayaran.")
            return redirect('transaksi-detail', pk=trx.pk)
        except ValidationError as exc:
            messages.error(request, str(exc.detail))
    return render(request, 'meditrack/kasir.html', {'formset': formset})


class TransaksiDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        trx = get_object_or_404(TransaksiPenjualan, pk=pk, user=request.user)
        return render(request, 'meditrack/transaksi_confirm_delete.html', {'object': trx})

    def post(self, request, pk):
        with transaction.atomic():
            trx = get_object_or_404(TransaksiPenjualan.objects.select_for_update(), pk=pk, user=request.user)
            if trx.status != 'DRAFT':
                messages.error(request, 'Hanya transaksi DRAFT dapat dihapus.')
                return redirect('transaksi-detail', pk=pk)
            trx.delete()
        messages.success(request, 'Transaksi draft dihapus.')
        return redirect('transaksi-list')


class TransaksiPayView(LoginRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(TransaksiPenjualan, pk=pk, user=request.user)
        try:
            pay_transaction(pk, request.user)
            messages.success(request, 'Pembayaran simulasi berhasil.')
        except ValidationError as exc:
            messages.error(request, str(exc.detail))
        return redirect('transaksi-detail', pk=pk)


class ObatViewSet(viewsets.ModelViewSet):
    queryset = Obat.objects.select_related("kategori", "supplier").all().order_by("-tanggal_masuk")
    serializer_class = ObatSerializer
    permission_classes = [StaffOrReadOnly]

    # Search + Ordering untuk feel ecommerce
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nama_obat", "kategori__nama_kategori", "supplier__nama_supplier"]
    ordering_fields = ["nama_obat", "harga", "stok", "tanggal_masuk"]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("nama_supplier")
    serializer_class = SupplierSerializer
    permission_classes = [StaffOrReadOnly]


class KategoriViewSet(viewsets.ModelViewSet):
    queryset = KategoriObat.objects.all().order_by("nama_kategori")
    serializer_class = KategoriSerializer
    permission_classes = [StaffOrReadOnly]


class DetailTransaksiViewSet(viewsets.ModelViewSet):
    serializer_class = DetailTransaksiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DetailTransaksi.objects.none()
        return DetailTransaksi.objects.filter(transaksi__user=self.request.user).select_related('obat', 'transaksi')

    @transaction.atomic
    def perform_create(self, serializer):
        trx = owned_draft(serializer.validated_data['transaksi'].pk, self.request.user)
        serializer.instance = save_item(trx, serializer.validated_data['obat'], serializer.validated_data['jumlah'])

    @transaction.atomic
    def perform_update(self, serializer):
        item = self.get_object()
        trx = owned_draft(item.transaksi_id, self.request.user)
        serializer.instance = save_item(trx, serializer.validated_data.get('obat', item.obat), serializer.validated_data.get('jumlah', item.jumlah), item=item)

    @transaction.atomic
    def perform_destroy(self, instance):
        trx = owned_draft(instance.transaksi_id, self.request.user)
        instance.delete()
        recalc(trx)


class TransaksiViewSet(viewsets.ModelViewSet):
    serializer_class = TransaksiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TransaksiPenjualan.objects.none()
        return TransaksiPenjualan.objects.filter(user=self.request.user).prefetch_related('detail__obat').order_by('-tanggal')

    def perform_create(self, serializer):
        serializer.instance = get_cart(self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        owned_draft(serializer.instance.pk, self.request.user)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        owned_draft(instance.pk, self.request.user).delete()

    @action(detail=False, methods=['GET'], url_path='my')
    def my_orders(self, request):
        return Response(self.get_serializer(self.get_queryset().exclude(status='DRAFT'), many=True).data)

    @action(detail=False, methods=['GET'], url_path='cart')
    def cart(self, request):
        return Response(self.get_serializer(get_cart(request.user)).data)

    @action(detail=False, methods=['POST'], url_path='cart/add')
    @transaction.atomic
    def cart_add(self, request):
        trx = get_cart(request.user)
        data = {**request.data, 'transaksi': trx.pk}
        ser = DetailTransaksiSerializer(data=data, context={'request': request})
        ser.is_valid(raise_exception=True)
        save_item(trx, ser.validated_data['obat'], ser.validated_data['jumlah'])
        trx.refresh_from_db()
        return Response(self.get_serializer(trx).data, status=201)

    @action(detail=False, methods=['patch'], url_path=r'cart/items/(?P<item_id>[0-9]+)')
    @transaction.atomic
    def cart_update_item(self, request, item_id=None):
        item = get_object_or_404(DetailTransaksi, pk=item_id, transaksi__user=request.user, transaksi__status='DRAFT')
        trx = owned_draft(item.transaksi_id, request.user)
        ser = DetailTransaksiSerializer(item, data=request.data, partial=True, context={'request': request})
        ser.is_valid(raise_exception=True)
        save_item(trx, ser.validated_data.get('obat', item.obat), ser.validated_data.get('jumlah', item.jumlah), item=item)
        trx.refresh_from_db()
        return Response(self.get_serializer(trx).data)

    @cart_update_item.mapping.delete
    @transaction.atomic
    def cart_delete_item(self, request, item_id=None):
        item = get_object_or_404(DetailTransaksi, pk=item_id, transaksi__user=request.user, transaksi__status='DRAFT')
        trx = owned_draft(item.transaksi_id, request.user)
        item.delete()
        recalc(trx)
        return Response(self.get_serializer(trx).data)

    @action(detail=False, methods=['POST'], url_path='cart/checkout')
    def cart_checkout(self, request):
        trx = self.get_queryset().filter(status='DRAFT').first()
        if not trx:
            raise ValidationError('Keranjang kosong.')
        return Response(self.get_serializer(checkout(trx.pk, request.user)).data)

    @action(detail=True, methods=['POST'], url_path='pay')
    def pay(self, request, pk=None):
        trx = self.get_object()
        return Response(self.get_serializer(pay_transaction(trx.pk, request.user)).data)
