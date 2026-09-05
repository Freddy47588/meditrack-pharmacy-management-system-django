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
    TransaksiForm, KasirItemForm
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

class HomeView(View):
    def get(self, request):
        context = {
            "total_obat": Obat.objects.count(),
            "total_supplier": Supplier.objects.count(),
            "total_kategori": KategoriObat.objects.count(),
            "total_transaksi": TransaksiPenjualan.objects.count(),
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


class ObatCreateView(CreateView):
    model = Obat
    form_class = ObatForm
    template_name = "meditrack/obat_form.html"
    success_url = reverse_lazy("obat-list")

    def form_valid(self, form):
        messages.success(self.request, "Obat berhasil ditambahkan!")
        return super().form_valid(form)


class ObatUpdateView(UpdateView):
    model = Obat
    form_class = ObatForm
    template_name = "meditrack/obat_form.html"
    success_url = reverse_lazy("obat-list")
    
    def form_valid(self, form):
        messages.success(self.request, "Obat berhasil diperbarui!")
        return super().form_valid(form)

    


class ObatDeleteView(DeleteView):
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

class SupplierCreateView(CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "meditrack/supplier_form.html"
    success_url = reverse_lazy("supplier-list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier berhasil ditambahkan!")
        return super().form_valid(form)


class SupplierUpdateView(UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "meditrack/supplier_form.html"
    success_url = reverse_lazy("supplier-list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier berhasil diperbarui!")
        return super().form_valid(form)



class SupplierDeleteView(DeleteView):
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

class KategoriCreateView(CreateView):
    model = KategoriObat
    form_class = KategoriForm
    template_name = "meditrack/kategori_form.html"
    success_url = reverse_lazy("kategori-list")

    def form_valid(self, form):
        messages.success(self.request, "Kategori berhasil ditambahkan!")
        return super().form_valid(form)


class KategoriUpdateView(UpdateView):
    model = KategoriObat
    form_class = KategoriForm
    template_name = "meditrack/kategori_form.html"
    success_url = reverse_lazy("kategori-list")

    def form_valid(self, form):
        messages.success(self.request, "Kategori berhasil diperbarui!")
        return super().form_valid(form)


class KategoriDeleteView(DeleteView):
    model = KategoriObat
    template_name = "meditrack/kategori_confirm_delete.html"
    success_url = reverse_lazy("kategori-list")


# =====================================================
# T R A N S A K S I
# =====================================================

class TransaksiListView(ListView):
    model = TransaksiPenjualan
    template_name = "meditrack/transaksi_list.html"
    context_object_name = "transaksi_list"


class TransaksiDetailView(DetailView):
    model = TransaksiPenjualan
    template_name = "meditrack/transaksi_detail.html"


class TransaksiCreateView(CreateView):
    model = TransaksiPenjualan
    form_class = TransaksiForm
    template_name = "meditrack/transaksi_form.html"
    success_url = reverse_lazy("transaksi-list")


# =====================================================
# K A S I R  ( F O R M S E T )
# =====================================================

def KasirView(request):
    KasirFormSet = formset_factory(KasirItemForm, extra=1)

    if request.method == "POST":
        formset = KasirFormSet(request.POST)

        if formset.is_valid():
            transaksi = TransaksiPenjualan.objects.create(total_harga=0)
            total = 0

            for item in formset.cleaned_data:
                obat = item.get("obat")
                jumlah = item.get("jumlah")

                if obat and jumlah:

                    # Validasi stok
                    if obat.stok < jumlah:
                        formset.add_error(None, f"Stok {obat.nama_obat} tidak mencukupi!")
                        transaksi.delete()
                        return render(request, "meditrack/kasir.html", {"formset": formset})

                    subtotal = obat.harga * jumlah
                    total += subtotal

                    # Buat detail transaksi
                    DetailTransaksi.objects.create(
                        transaksi=transaksi,
                        obat=obat,
                        jumlah=jumlah,
                        subtotal=subtotal,
                    )

                    # Kurangi stok obat
                    obat.stok -= jumlah
                    obat.save()

            transaksi.total_harga = total
            transaksi.save()

            return redirect("transaksi-detail", pk=transaksi.pk)

    else:
        formset = KasirFormSet()

    return render(request, "meditrack/kasir.html", {"formset": formset})


# =====================================================
# H A P U S  T R A N S A K S I
# =====================================================

class TransaksiDeleteView(View):
    def get(self, request, pk):
        transaksi = get_object_or_404(TransaksiPenjualan, pk=pk)
        return render(request, "meditrack/transaksi_confirm_delete.html", {"object": transaksi})

    def post(self, request, pk):
        transaksi = get_object_or_404(TransaksiPenjualan, pk=pk)

        # Kembalikan stok obat
        for item in transaksi.detail.all():
            item.obat.stok += item.jumlah
            item.obat.save()

        transaksi.detail.all().delete()
        transaksi.delete()

        return redirect("transaksi-list")


# =====================================================
# A P I  ( D R F )  - UAS DECOUPLED (ECOMMERCE FLOW)
# =====================================================

class ObatViewSet(viewsets.ModelViewSet):
    queryset = Obat.objects.select_related("kategori", "supplier").all().order_by("-tanggal_masuk")
    serializer_class = ObatSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Search + Ordering untuk feel ecommerce
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nama_obat", "kategori__nama_kategori", "supplier__nama_supplier"]
    ordering_fields = ["nama_obat", "harga", "stok", "tanggal_masuk"]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("nama_supplier")
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class KategoriViewSet(viewsets.ModelViewSet):
    queryset = KategoriObat.objects.all().order_by("nama_kategori")
    serializer_class = KategoriSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class DetailTransaksiViewSet(viewsets.ModelViewSet):
    queryset = DetailTransaksi.objects.select_related("obat", "transaksi").all()
    serializer_class = DetailTransaksiSerializer
    permission_classes = [IsAuthenticated]


class TransaksiViewSet(viewsets.ModelViewSet):
    serializer_class = TransaksiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TransaksiPenjualan.objects.filter(user=self.request.user).order_by("-tanggal")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _recalc_total(self, trx: TransaksiPenjualan):
        total = trx.detail.aggregate(t=Sum("subtotal"))["t"] or 0
        trx.total_harga = total
        trx.save(update_fields=["total_harga"])

    # ===== Riwayat pesanan =====
    @action(detail=False, methods=["GET"], url_path="my")
    def my_orders(self, request):
        qs = self.get_queryset().exclude(status="DRAFT")
        return Response(self.get_serializer(qs, many=True).data)

    # ===== CART =====
    @action(detail=False, methods=["GET"], url_path="cart")
    def cart(self, request):
        trx, _ = TransaksiPenjualan.objects.get_or_create(
            user=request.user, status="DRAFT"
        )
        return Response(self.get_serializer(trx).data)

    @action(detail=False, methods=["POST"], url_path="cart/add")
    def cart_add(self, request):
        trx, _ = TransaksiPenjualan.objects.get_or_create(
            user=request.user, status="DRAFT"
        )

        data = request.data.copy()
        data["transaksi"] = trx.id

        ser = DetailTransaksiSerializer(data=data)
        ser.is_valid(raise_exception=True)
        ser.save()

        self._recalc_total(trx)
        return Response(self.get_serializer(trx).data, status=status.HTTP_201_CREATED)

    # ===== UPDATE ITEM CART =====
    @action(detail=False, methods=["patch"], url_path=r"cart/items/(?P<item_id>[^/.]+)")
    def cart_update_item(self, request, item_id=None):
        trx = TransaksiPenjualan.objects.filter(
            user=request.user, status="DRAFT"
        ).first()
        if not trx:
            return Response({"detail": "Keranjang kosong."}, status=400)

        item = trx.detail.filter(id=item_id).first()
        if not item:
            return Response({"detail": "Item tidak ditemukan."}, status=404)

        ser = DetailTransaksiSerializer(item, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()

        self._recalc_total(trx)
        return Response(self.get_serializer(trx).data)

    # ===== DELETE ITEM CART =====
    @action(detail=False, methods=["delete"], url_path=r"cart/items/(?P<item_id>[^/.]+)")
    def cart_delete_item(self, request, item_id=None):
        trx = TransaksiPenjualan.objects.filter(
            user=request.user, status="DRAFT"
        ).first()
        if not trx:
            return Response({"detail": "Keranjang kosong."}, status=400)

        item = trx.detail.filter(id=item_id).first()
        if not item:
            return Response({"detail": "Item tidak ditemukan."}, status=404)

        item.delete()
        self._recalc_total(trx)
        return Response(self.get_serializer(trx).data)

    # ===== CHECKOUT =====
    @action(detail=False, methods=["POST"], url_path="cart/checkout")
    def cart_checkout(self, request):
        trx = TransaksiPenjualan.objects.filter(
            user=request.user, status="DRAFT"
        ).first()
        if not trx or trx.detail.count() == 0:
            return Response({"detail": "Keranjang kosong."}, status=400)

        with transaction.atomic():
            for item in trx.detail.select_related("obat").all():
                if item.obat.stok < item.jumlah:
                    return Response(
                        {"detail": f"Stok tidak cukup untuk {item.obat.nama_obat}."},
                        status=400
                    )
                item.obat.stok -= item.jumlah
                item.obat.save(update_fields=["stok"])

            self._recalc_total(trx)
            trx.status = "PENDING"
            trx.save(update_fields=["status"])

        return Response(self.get_serializer(trx).data)

    # ===== PAY =====
    @action(detail=True, methods=["POST"], url_path="pay")
    def pay(self, request, pk=None):
        trx = self.get_object()
        if trx.status != "PENDING":
            return Response(
                {"detail": "Transaksi harus PENDING untuk dibayar."},
                status=400
            )

        trx.status = "PAID"
        trx.save(update_fields=["status"])
        return Response(self.get_serializer(trx).data)


