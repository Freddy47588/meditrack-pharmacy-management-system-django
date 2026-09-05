"""Shared atomic transaction operations for HTML and REST entry points."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from .models import DetailTransaksi, Obat, StockMovement, TransaksiPenjualan


def require_draft(trx):
    if trx.status != "DRAFT":
        raise ValidationError("Hanya transaksi DRAFT dapat diubah.")


def owned_draft(pk, user):
    trx = get_object_or_404(
        TransaksiPenjualan.objects.select_for_update(), pk=pk, user=user
    )
    require_draft(trx)
    return trx


@transaction.atomic
def get_cart(user):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    trx = (
        TransaksiPenjualan.objects.filter(user=user, status="DRAFT")
        .order_by("pk")
        .first()
    )
    return trx or TransaksiPenjualan.objects.create(user=user)


def recalc(trx):
    trx.total_harga = trx.detail.aggregate(total=Sum("subtotal"))["total"] or Decimal(
        "0"
    )
    if trx.total_harga > Decimal("9999999999.99"):
        raise ValidationError("Total melebihi batas transaksi.")
    trx.save(update_fields=["total_harga"])


@transaction.atomic
def save_item(trx, obat, jumlah, item=None):
    trx = owned_draft(trx.pk, trx.user)
    obat = Obat.objects.select_for_update().get(pk=obat.pk)
    duplicate = trx.detail.filter(obat=obat)
    if item:
        if duplicate.exclude(pk=item.pk).exists():
            raise ValidationError({"obat": "Obat sudah ada di keranjang."})
    else:
        item = duplicate.first()
        if item:
            jumlah += item.jumlah
    if jumlah <= 0 or jumlah > obat.stok:
        raise ValidationError(
            {"jumlah": "Jumlah harus positif dan tidak melebihi stok."}
        )
    if obat.expiry_status == "expired":
        raise ValidationError({"obat": "Obat kedaluwarsa tidak dapat dijual."})
    subtotal = obat.harga * jumlah
    if subtotal > Decimal("9999999999.99"):
        raise ValidationError({"jumlah": "Subtotal melebihi batas transaksi."})
    if item:
        item.obat, item.jumlah, item.subtotal = obat, jumlah, subtotal
        item.save()
    else:
        item = DetailTransaksi.objects.create(
            transaksi=trx, obat=obat, jumlah=jumlah, subtotal=subtotal
        )
    recalc(trx)
    return item


@transaction.atomic
def checkout(pk, user):
    trx = owned_draft(pk, user)
    items = list(trx.detail.select_related("obat").order_by("obat_id", "pk"))
    if not items:
        raise ValidationError("Keranjang kosong.")
    for item in items:
        obat = Obat.objects.select_for_update().get(pk=item.obat_id)
        if obat.expiry_status == "expired":
            raise ValidationError(f"{obat.nama_obat} sudah kedaluwarsa.")
        if item.jumlah <= 0 or not Obat.objects.filter(
            pk=obat.pk, stok__gte=item.jumlah
        ).update(stok=F("stok") - item.jumlah):
            raise ValidationError(f"Stok tidak cukup untuk {obat.nama_obat}.")
        StockMovement.objects.create(
            obat=obat,
            tipe="SALE",
            quantity=item.jumlah,
            stock_before=obat.stok,
            stock_after=obat.stok - item.jumlah,
            user=user,
            reference=f"transaksi:{trx.pk}",
        )
        item.subtotal = obat.harga * item.jumlah
        item.save(update_fields=["subtotal"])
    recalc(trx)
    trx.status = "PENDING"
    trx.save(update_fields=["status"])
    return trx


@transaction.atomic
def pay_transaction(pk, user):
    trx = get_object_or_404(
        TransaksiPenjualan.objects.select_for_update(), pk=pk, user=user
    )
    if trx.status != "PENDING":
        raise ValidationError("Transaksi harus PENDING untuk dibayar.")
    trx.status = "PAID"
    trx.save(update_fields=["status"])
    return trx


def record_adjustment(obat, before, user, note="Perubahan stok manual"):
    if before != obat.stok:
        StockMovement.objects.create(
            obat=obat,
            tipe="ADJUSTMENT",
            quantity=abs(obat.stok - before),
            stock_before=before,
            stock_after=obat.stok,
            user=user,
            note=note,
        )


@transaction.atomic
def restock(pk, quantity, user, note=""):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError(
            {"quantity": "Jumlah restock harus bilangan bulat positif."}
        )
    obat = get_object_or_404(Obat.objects.select_for_update(), pk=pk)
    before = obat.stok
    if before + quantity > 2147483647:
        raise ValidationError({"quantity": "Stok melebihi batas yang didukung."})
    obat.stok += quantity
    obat.save(update_fields=["stok"])
    StockMovement.objects.create(
        obat=obat,
        tipe="IN",
        quantity=quantity,
        stock_before=before,
        stock_after=obat.stok,
        user=user,
        note=note,
    )
    return obat
