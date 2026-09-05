from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from meditrack.models import DetailTransaksi, Obat, StockMovement, TransaksiPenjualan
from meditrack.services import restock

from .test_api import APIData


class InventoryTests(APIData):
    def setUp(self):
        self.user.is_staff = True
        self.user.save()
        self.authenticate()
        self.client.force_login(self.user)

    def test_minimum_stock_boundaries(self):
        self.obat.minimum_stock = 12
        self.assertEqual(self.obat.stock_status, "low")
        self.obat.stok = 12
        self.assertEqual(self.obat.stock_status, "low")
        self.obat.stok = 13
        self.assertEqual(self.obat.stock_status, "safe")
        self.obat.stok = 0
        self.assertEqual(self.obat.stock_status, "empty")

    def test_expiry_boundaries_and_missing_date(self):
        self.assertEqual(self.obat.expiry_status, "unknown")
        for days, expected in [
            (-1, "expired"),
            (0, "near_expiry"),
            (30, "near_expiry"),
            (31, "safe"),
        ]:
            self.obat.expiry_date = timezone.localdate() + timedelta(days=days)
            self.assertEqual(self.obat.expiry_status, expected)

    def test_restock_records_actor_before_after_and_note(self):
        response = self.client.post(
            f"/obat/{self.obat.pk}/restock/", {"quantity": 7, "note": "Delivery"}
        )
        self.assertEqual(response.status_code, 302)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 17)
        movement = StockMovement.objects.get()
        self.assertEqual(
            (
                movement.tipe,
                movement.quantity,
                movement.stock_before,
                movement.stock_after,
            ),
            ("IN", 7, 10, 17),
        )
        self.assertEqual(movement.user, self.user)
        self.assertEqual(movement.note, "Delivery")

    def test_invalid_restock_quantity_has_no_side_effects(self):
        for quantity in [0, -1, "abc", "1.5", 2147483648]:
            self.assertEqual(
                self.client.post(
                    f"/obat/{self.obat.pk}/restock/", {"quantity": quantity}
                ).status_code,
                200,
            )
        for quantity in [0, -1, True, 1.5, "2"]:
            with self.assertRaises(ValidationError):
                restock(self.obat.pk, quantity, self.user)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)
        self.assertFalse(StockMovement.objects.exists())

    def test_restock_is_atomic_when_audit_write_fails(self):
        with patch(
            "meditrack.services.StockMovement.objects.create", side_effect=RuntimeError
        ):
            with self.assertRaises(RuntimeError):
                restock(self.obat.pk, 3, self.user)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_checkout_records_sale_once_and_rolls_back_on_later_failure(self):
        self.client.post(
            "/api/transaksi/cart/add/",
            {"obat": self.obat.pk, "jumlah": 2},
            format="json",
        )
        second = Obat.objects.create(
            nama_obat="Second",
            kategori=self.kategori,
            supplier=self.supplier,
            harga=1,
            stok=1,
        )
        self.client.post(
            "/api/transaksi/cart/add/", {"obat": second.pk, "jumlah": 1}, format="json"
        )
        second.stok = 0
        second.save()
        self.assertEqual(
            self.client.post("/api/transaksi/cart/checkout/").status_code, 400
        )
        self.assertFalse(StockMovement.objects.exists())
        second.stok = 1
        second.save()
        self.assertEqual(
            self.client.post("/api/transaksi/cart/checkout/").status_code, 200
        )
        self.assertEqual(StockMovement.objects.filter(tipe="SALE").count(), 2)
        movement = StockMovement.objects.get(obat=self.obat)
        self.assertEqual((movement.stock_before, movement.stock_after), (10, 8))
        self.assertEqual(
            movement.reference, f"transaksi:{TransaksiPenjualan.objects.get().pk}"
        )
        self.assertEqual(
            self.client.post("/api/transaksi/cart/checkout/").status_code, 400
        )
        self.assertEqual(StockMovement.objects.count(), 2)

    def test_kasir_records_sale(self):
        response = self.client.post(
            "/kasir/",
            {
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 0,
                "form-0-obat": self.obat.pk,
                "form-0-jumlah": 2,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StockMovement.objects.get().tipe, "SALE")

    def test_api_manual_adjustment_and_metadata_only_update(self):
        self.client.patch(f"/api/obat/{self.obat.pk}/", {"stok": 4}, format="json")
        movement = StockMovement.objects.get()
        self.assertEqual(
            (
                movement.tipe,
                movement.quantity,
                movement.stock_before,
                movement.stock_after,
            ),
            ("ADJUSTMENT", 6, 10, 4),
        )
        self.client.patch(
            f"/api/obat/{self.obat.pk}/", {"nama_obat": "New name"}, format="json"
        )
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_html_manual_adjustment(self):
        response = self.client.post(
            f"/obat/{self.obat.pk}/edit/",
            {
                "nama_obat": self.obat.nama_obat,
                "kategori": self.kategori.pk,
                "supplier": self.supplier.pk,
                "harga": self.obat.harga,
                "stok": 6,
                "minimum_stock": 3,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StockMovement.objects.get().stock_after, 6)

    def test_expired_product_rejected_at_add_and_checkout(self):
        self.client.post(
            "/api/transaksi/cart/add/",
            {"obat": self.obat.pk, "jumlah": 2},
            format="json",
        )
        self.obat.expiry_date = timezone.localdate() - timedelta(days=1)
        self.obat.save()
        self.assertEqual(
            self.client.post(
                "/api/transaksi/cart/add/",
                {"obat": self.obat.pk, "jumlah": 1},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/transaksi/cart/checkout/").status_code, 400
        )
        self.assertFalse(StockMovement.objects.exists())

    def test_database_constraints_zero_quantity_and_negative_price(self):
        trx = TransaksiPenjualan.objects.create(user=self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            DetailTransaksi.objects.create(
                transaksi=trx, obat=self.obat, jumlah=0, subtotal=0
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Obat.objects.filter(pk=self.obat.pk).update(harga=-1)

    def test_restock_staff_only_and_inventory_filter(self):
        self.obat.minimum_stock = 15
        self.obat.save()
        response = self.client.get("/obat/?inventory=low")
        self.assertContains(response, self.obat.nama_obat)
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.post(
                f"/obat/{self.obat.pk}/restock/", {"quantity": 2}
            ).status_code,
            403,
        )

    def test_history_protects_catalog_deletion(self):
        restock(self.obat.pk, 1, self.user)
        for kind, pk in [
            ("obat", self.obat.pk),
            ("kategori", self.kategori.pk),
            ("supplier", self.supplier.pk),
        ]:
            self.assertEqual(self.client.delete(f"/api/{kind}/{pk}/").status_code, 400)
            self.assertEqual(self.client.post(f"/{kind}/{pk}/hapus/").status_code, 302)
