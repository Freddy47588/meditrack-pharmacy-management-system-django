from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.views import View
from django.urls import reverse_lazy
from django.forms import formset_factory
from rest_framework import generics, viewsets
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
# A P I  ( D R F )
# =====================================================


class ObatViewSet(viewsets.ModelViewSet):
    queryset = Obat.objects.all()
    serializer_class = ObatSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class KategoriViewSet(viewsets.ModelViewSet):
    queryset = KategoriObat.objects.all()
    serializer_class = KategoriSerializer


class TransaksiViewSet(viewsets.ModelViewSet):
    queryset = TransaksiPenjualan.objects.all()
    serializer_class = TransaksiSerializer


class DetailTransaksiViewSet(viewsets.ModelViewSet):
    queryset = DetailTransaksi.objects.all()
    serializer_class = DetailTransaksiSerializer
