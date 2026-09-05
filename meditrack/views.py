from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import KasirItemForm, KategoriForm, ObatForm, RestockForm, SupplierForm
from .models import DetailTransaksi, KategoriObat, Obat, Supplier, TransaksiPenjualan
from .permissions import StaffOrReadOnly
from .serializers import (
    CartAddSerializer,
    CartUpdateSerializer,
    DetailTransaksiSerializer,
    KategoriSerializer,
    ObatSerializer,
    SupplierSerializer,
    TransaksiSerializer,
)
from .services import (
    checkout,
    get_cart,
    owned_draft,
    pay_transaction,
    recalc,
    record_adjustment,
    restock,
    save_item,
)


class StaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class OwnedMixin(LoginRequiredMixin):
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class SearchListMixin:
    paginate_by = 12
    search_field = ""
    sort_fields = ()

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query and self.search_field:
            qs = qs.filter(**{self.search_field + "__icontains": query})
        ordering = self.request.GET.get("sort", "")
        return qs.order_by(ordering if ordering in self.sort_fields else "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_params"] = params.urlencode()
        return context


class DeleteMessageMixin:
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Data masih digunakan. Hapus relasi katalog yang tidak dipakai; riwayat transaksi dan stok tetap dilindungi.",
            )
            return redirect(self.success_url)
        messages.success(self.request, "Data berhasil dihapus.")
        return response


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        start = today - timedelta(days=6)
        inventory = Obat.objects.aggregate(
            total_obat=Count("pk"),
            low_stock=Count("pk", filter=Q(stok__gt=0, stok__lte=F("minimum_stock"))),
            out_of_stock=Count("pk", filter=Q(stok=0)),
            near_expiry=Count(
                "pk",
                filter=Q(
                    expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30)
                ),
            ),
            expired=Count("pk", filter=Q(expiry_date__lt=today)),
        )
        own = TransaksiPenjualan.objects.filter(user=request.user)
        paid = own.filter(status="PAID")
        sales = dict(
            paid.filter(tanggal__date__gte=start, tanggal__date__lte=today)
            .annotate(day=TruncDate("tanggal"))
            .values("day")
            .annotate(total=Sum("total_harga"))
            .values_list("day", "total")
        )
        days = [start + timedelta(days=i) for i in range(7)]
        context = {
            **inventory,
            "total_supplier": Supplier.objects.count(),
            "total_kategori": KategoriObat.objects.count(),
            "transactions_today": own.filter(tanggal__date=today)
            .exclude(status="DRAFT")
            .count(),
            "sales_today": paid.filter(tanggal__date=today).aggregate(
                total=Sum("total_harga")
            )["total"]
            or 0,
            "recent_transactions": own.exclude(status="DRAFT")
            .select_related("user")
            .order_by("-tanggal", "-pk")[:5],
            "top_products": DetailTransaksi.objects.filter(transaksi__in=paid)
            .values("obat_id", "obat__nama_obat")
            .annotate(quantity=Sum("jumlah"), revenue=Sum("subtotal"))
            .order_by("-quantity", "obat_id")[:5],
            "inventory_alerts": Obat.objects.filter(
                Q(stok__lte=F("minimum_stock"))
                | Q(expiry_date__lte=today + timedelta(days=30))
            ).order_by("stok", "expiry_date", "pk")[:10],
            "chart_labels": [day.strftime("%d %b") for day in days],
            "chart_values": [float(sales.get(day, 0)) for day in days],
            "daily_sales": [(day, sales.get(day, 0)) for day in days],
            "today": today,
        }
        return render(request, "meditrack/home.html", context)


class ObatListView(SearchListMixin, ListView):
    search_field = "nama_obat"
    sort_fields = ("nama_obat", "-nama_obat")
    model = Obat
    template_name = "meditrack/obat_list.html"
    context_object_name = "obat_list"

    def get_queryset(self):
        qs = super().get_queryset().select_related("kategori", "supplier")
        filters = {
            "low": {"stok__gt": 0, "stok__lte": F("minimum_stock")},
            "empty": {"stok": 0},
            "expired": {"expiry_date__lt": timezone.localdate()},
            "near_expiry": {
                "expiry_date__gte": timezone.localdate(),
                "expiry_date__lte": timezone.localdate() + timedelta(days=30),
            },
        }
        return qs.filter(**filters.get(self.request.GET.get("inventory"), {}))


class ObatDetailView(DetailView):
    model = Obat
    template_name = "meditrack/obat_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["movements"] = (
            self.object.stock_movements.select_related("user")[:50]
            if self.request.user.is_staff
            else []
        )
        return context


class InventorySaveMixin:
    @transaction.atomic
    def form_valid(self, form):
        before = (
            Obat.objects.select_for_update().get(pk=form.instance.pk).stok
            if form.instance.pk
            else 0
        )
        response = super().form_valid(form)
        record_adjustment(self.object, before, self.request.user)
        if self.object.stock_status != "safe":
            messages.warning(
                self.request, "Stok obat berada pada atau di bawah batas minimum."
            )
        return response


class RestockView(StaffMixin, View):
    def get(self, request, pk):
        obat = get_object_or_404(Obat, pk=pk)
        return render(
            request, "meditrack/restock.html", {"object": obat, "form": RestockForm()}
        )

    def post(self, request, pk):
        obat = get_object_or_404(Obat, pk=pk)
        form = RestockForm(request.POST)
        if form.is_valid():
            try:
                restock(
                    pk,
                    form.cleaned_data["quantity"],
                    request.user,
                    form.cleaned_data["note"],
                )
                messages.success(request, "Restock berhasil dicatat.")
                return redirect("obat-detail", pk=pk)
            except ValidationError as exc:
                form.add_error(None, str(exc.detail))
        return render(request, "meditrack/restock.html", {"object": obat, "form": form})


class ObatCreateView(StaffMixin, InventorySaveMixin, CreateView):
    model = Obat
    form_class = ObatForm
    template_name = "meditrack/obat_form.html"
    success_url = reverse_lazy("obat-list")

    def form_valid(self, form):
        messages.success(self.request, "Obat berhasil ditambahkan!")
        return super().form_valid(form)


class ObatUpdateView(StaffMixin, InventorySaveMixin, UpdateView):
    model = Obat
    form_class = ObatForm
    template_name = "meditrack/obat_form.html"
    success_url = reverse_lazy("obat-list")

    def form_valid(self, form):
        messages.success(self.request, "Obat berhasil diperbarui!")
        return super().form_valid(form)


class ObatDeleteView(StaffMixin, DeleteMessageMixin, DeleteView):
    model = Obat
    template_name = "meditrack/obat_confirm_delete.html"
    success_url = reverse_lazy("obat-list")


class SupplierListView(SearchListMixin, ListView):
    search_field = "nama_supplier"
    sort_fields = ("nama_supplier", "-nama_supplier")
    model = Supplier
    template_name = "meditrack/supplier_list.html"
    context_object_name = "supplier_list"


class SupplierDetailView(DetailView):
    model = Supplier
    template_name = "meditrack/supplier_detail.html"


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


class SupplierDeleteView(StaffMixin, DeleteMessageMixin, DeleteView):
    model = Supplier
    template_name = "meditrack/supplier_confirm_delete.html"
    success_url = reverse_lazy("supplier-list")


class KategoriListView(SearchListMixin, ListView):
    search_field = "nama_kategori"
    sort_fields = ("nama_kategori", "-nama_kategori")
    model = KategoriObat
    template_name = "meditrack/kategori_list.html"
    context_object_name = "kategori_list"


class KategoriDetailView(DetailView):
    model = KategoriObat
    template_name = "meditrack/kategori_detail.html"


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


class KategoriDeleteView(StaffMixin, DeleteMessageMixin, DeleteView):
    model = KategoriObat
    template_name = "meditrack/kategori_confirm_delete.html"
    success_url = reverse_lazy("kategori-list")


class TransaksiListView(OwnedMixin, SearchListMixin, ListView):
    search_field = "id"
    sort_fields = ("tanggal", "-tanggal", "total_harga", "-total_harga")

    def get_queryset(self):
        qs = super().get_queryset()
        state = self.request.GET.get("status")
        return (
            qs.filter(status=state)
            if state in dict(TransaksiPenjualan.STATUS_CHOICES)
            else qs
        )

    model = TransaksiPenjualan
    template_name = "meditrack/transaksi_list.html"
    context_object_name = "transaksi_list"


class TransaksiDetailView(OwnedMixin, DetailView):
    model = TransaksiPenjualan
    template_name = "meditrack/transaksi_detail.html"


class TransaksiCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("kasir")

    post = get


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
                        save_item(trx, row["obat"], row["jumlah"])
                trx = checkout(trx.pk, request.user)
            messages.success(
                request, "Checkout berhasil. Transaksi menunggu pembayaran."
            )
            return redirect("transaksi-detail", pk=trx.pk)
        except ValidationError as exc:
            messages.error(request, str(exc.detail))
    return render(
        request,
        "meditrack/kasir.html",
        {
            "formset": formset,
            "products": list(Obat.objects.values("id", "nama_obat", "harga", "stok")),
        },
    )


class TransaksiDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        trx = get_object_or_404(TransaksiPenjualan, pk=pk, user=request.user)
        return render(
            request, "meditrack/transaksi_confirm_delete.html", {"object": trx}
        )

    def post(self, request, pk):
        with transaction.atomic():
            trx = get_object_or_404(
                TransaksiPenjualan.objects.select_for_update(), pk=pk, user=request.user
            )
            if trx.status != "DRAFT":
                messages.error(request, "Hanya transaksi DRAFT dapat dihapus.")
                return redirect("transaksi-detail", pk=pk)
            trx.delete()
        messages.success(request, "Transaksi draft dihapus.")
        return redirect("transaksi-list")


class TransaksiPayView(LoginRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(TransaksiPenjualan, pk=pk, user=request.user)
        try:
            pay_transaction(pk, request.user)
            messages.success(request, "Pembayaran simulasi berhasil.")
        except ValidationError as exc:
            messages.error(request, str(exc.detail))
        return redirect("transaksi-detail", pk=pk)


class ProtectedDeleteMixin:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                "Data masih dirujuk oleh katalog atau riwayat transaksi/stok."
            )


class ObatViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = (
        Obat.objects.select_related("kategori", "supplier")
        .all()
        .order_by("-tanggal_masuk")
    )
    serializer_class = ObatSerializer
    permission_classes = [StaffOrReadOnly]

    @transaction.atomic
    def perform_create(self, serializer):
        obat = serializer.save()
        record_adjustment(obat, 0, self.request.user, "Stok awal katalog")

    @transaction.atomic
    def perform_update(self, serializer):
        locked = Obat.objects.select_for_update().get(pk=serializer.instance.pk)
        before = locked.stok
        serializer.instance = locked
        obat = serializer.save()
        record_adjustment(obat, before, self.request.user)

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nama_obat", "kategori__nama_kategori", "supplier__nama_supplier"]
    ordering_fields = ["nama_obat", "harga", "stok", "tanggal_masuk"]


class SupplierViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("nama_supplier")
    serializer_class = SupplierSerializer
    permission_classes = [StaffOrReadOnly]


class KategoriViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = KategoriObat.objects.all().order_by("nama_kategori")
    serializer_class = KategoriSerializer
    permission_classes = [StaffOrReadOnly]


class DetailTransaksiViewSet(viewsets.ModelViewSet):
    serializer_class = DetailTransaksiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DetailTransaksi.objects.none()
        return DetailTransaksi.objects.filter(
            transaksi__user=self.request.user
        ).select_related("obat", "transaksi")

    @transaction.atomic
    def perform_create(self, serializer):
        trx = owned_draft(serializer.validated_data["transaksi"].pk, self.request.user)
        serializer.instance = save_item(
            trx, serializer.validated_data["obat"], serializer.validated_data["jumlah"]
        )

    @transaction.atomic
    def perform_update(self, serializer):
        item = self.get_object()
        trx = owned_draft(item.transaksi_id, self.request.user)
        serializer.instance = save_item(
            trx,
            serializer.validated_data.get("obat", item.obat),
            serializer.validated_data.get("jumlah", item.jumlah),
            item=item,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        trx = owned_draft(instance.transaksi_id, self.request.user)
        instance.delete()
        recalc(trx)


class TransaksiViewSet(viewsets.ModelViewSet):
    serializer_class = TransaksiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TransaksiPenjualan.objects.none()
        return (
            TransaksiPenjualan.objects.filter(user=self.request.user)
            .prefetch_related("detail__obat")
            .order_by("-tanggal")
        )

    def perform_create(self, serializer):
        serializer.instance = get_cart(self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = owned_draft(serializer.instance.pk, self.request.user)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        owned_draft(instance.pk, self.request.user).delete()

    @extend_schema(
        responses=TransaksiSerializer(many=True),
        description="Riwayat transaksi sendiri selain DRAFT.",
    )
    @action(detail=False, methods=["GET"], url_path="my")
    def my_orders(self, request):
        return Response(
            self.get_serializer(
                self.get_queryset().exclude(status="DRAFT"), many=True
            ).data
        )

    @extend_schema(
        responses=TransaksiSerializer(many=False),
        description="Ambil atau buat satu keranjang DRAFT milik pengguna.",
    )
    @action(detail=False, methods=["GET"], url_path="cart")
    def cart(self, request):
        return Response(self.get_serializer(get_cart(request.user)).data)

    @extend_schema(
        request=CartAddSerializer,
        responses={201: TransaksiSerializer},
        description="Tambah item; obat yang sama digabungkan. Stok belum dikurangi.",
    )
    @action(detail=False, methods=["POST"], url_path="cart/add")
    @transaction.atomic
    def cart_add(self, request):
        trx = get_cart(request.user)
        data = request.data.copy()
        data["transaksi"] = trx.pk
        ser = DetailTransaksiSerializer(data=data, context={"request": request})
        ser.is_valid(raise_exception=True)
        save_item(trx, ser.validated_data["obat"], ser.validated_data["jumlah"])
        trx.refresh_from_db()
        return Response(self.get_serializer(trx).data, status=201)

    @extend_schema(
        request=CartUpdateSerializer,
        responses=TransaksiSerializer,
        description="Ganti jumlah/obat pada item DRAFT milik pengguna.",
    )
    @action(detail=False, methods=["patch"], url_path=r"cart/items/(?P<item_id>[0-9]+)")
    @transaction.atomic
    def cart_update_item(self, request, item_id=None):
        item = get_object_or_404(
            DetailTransaksi,
            pk=item_id,
            transaksi__user=request.user,
            transaksi__status="DRAFT",
        )
        trx = owned_draft(item.transaksi_id, request.user)
        ser = DetailTransaksiSerializer(
            item, data=request.data, partial=True, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        save_item(
            trx,
            ser.validated_data.get("obat", item.obat),
            ser.validated_data.get("jumlah", item.jumlah),
            item=item,
        )
        trx.refresh_from_db()
        return Response(self.get_serializer(trx).data)

    @extend_schema(
        request=None,
        responses={200: TransaksiSerializer},
        description="Hapus item DRAFT dan hitung ulang total.",
    )
    @cart_update_item.mapping.delete
    @transaction.atomic
    def cart_delete_item(self, request, item_id=None):
        item = get_object_or_404(
            DetailTransaksi,
            pk=item_id,
            transaksi__user=request.user,
            transaksi__status="DRAFT",
        )
        trx = owned_draft(item.transaksi_id, request.user)
        item.delete()
        recalc(trx)
        return Response(self.get_serializer(trx).data)

    @extend_schema(
        request=None,
        responses=TransaksiSerializer,
        description="DRAFT ke PENDING secara atomic; validasi expiry, harga, stok, dan catat SALE.",
    )
    @action(detail=False, methods=["POST"], url_path="cart/checkout")
    def cart_checkout(self, request):
        trx = self.get_queryset().filter(status="DRAFT").order_by("pk").first()
        if not trx:
            raise ValidationError("Keranjang kosong.")
        return Response(self.get_serializer(checkout(trx.pk, request.user)).data)

    @extend_schema(
        request=None,
        responses=TransaksiSerializer,
        description="Simulasi pembayaran: hanya PENDING ke PAID.",
    )
    @action(detail=True, methods=["POST"], url_path="pay")
    def pay(self, request, pk=None):
        trx = self.get_object()
        return Response(self.get_serializer(pay_transaction(trx.pk, request.user)).data)
