from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from meditrack.models import Obat, StockMovement, TransaksiPenjualan

from .test_api import APIData


@override_settings(DEBUG=True)
class DemoSeedTests(TestCase):
    def seed(self):
        call_command("seed_demo", stdout=StringIO())

    def test_demo_is_repeatable_without_changing_stock_or_creating_password(self):
        self.seed()
        before = list(Obat.objects.values_list("pk", "stok"))
        movements = StockMovement.objects.count()
        self.seed()
        self.assertEqual(list(Obat.objects.values_list("pk", "stok")), before)
        self.assertEqual(StockMovement.objects.count(), movements)
        self.assertEqual(TransaksiPenjualan.objects.count(), 8)
        self.assertEqual(Obat.objects.count(), 14)
        self.assertFalse(get_user_model().objects.get().has_usable_password())
        self.assertFalse(StockMovement.objects.filter(stock_after__lt=0).exists())

    def test_existing_database_is_untouched(self):
        get_user_model().objects.create_user("existing")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(Obat.objects.exists())
        self.assertEqual(get_user_model().objects.count(), 1)

    @override_settings(DEBUG=False)
    def test_production_seed_is_refused(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(get_user_model().objects.exists())


class PortfolioSmokeTests(APIData):
    def setUp(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def test_all_main_html_routes_render(self):
        from meditrack.models import TransaksiPenjualan

        trx = TransaksiPenjualan.objects.create(user=self.user)
        paths = [
            "/",
            "/login/",
            "/kasir/",
            "/transaksi/",
            f"/transaksi/{trx.pk}/",
            f"/transaksi/{trx.pk}/hapus/",
        ]
        for resource, pk in [
            ("obat", self.obat.pk),
            ("supplier", self.supplier.pk),
            ("kategori", self.kategori.pk),
        ]:
            paths.extend(
                [
                    f"/{resource}/",
                    f"/{resource}/tambah/",
                    f"/{resource}/{pk}/edit/",
                    f"/{resource}/{pk}/hapus/",
                ]
            )
            paths.append(f"/{resource}/{pk}/")
        paths.append(f"/obat/{self.obat.pk}/restock/")
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "meditrack/base.html")

    def test_pagination_preserves_filters_and_sort_is_allowlisted(self):
        for i in range(15):
            Obat.objects.create(
                nama_obat=f"Test {i}",
                kategori=self.kategori,
                supplier=self.supplier,
                harga=1,
                stok=1,
            )
        response = self.client.get("/obat/?q=Test&sort=nama_obat&inventory=low&page=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["obat_list"]), 3)
        self.assertContains(response, "q=Test")
        self.assertEqual(self.client.get("/obat/?sort=not_a_field").status_code, 200)

    def test_schema_documents_both_cart_item_methods(self):
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        item_path = schema["paths"]["/api/transaksi/cart/items/{item_id}/"]
        self.assertIn("patch", item_path)
        self.assertIn("delete", item_path)
        self.assertNotIn(
            "requestBody", schema["paths"]["/api/transaksi/cart/checkout/"]["post"]
        )
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)

    def test_logout_is_post_only(self):
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertEqual(self.client.post("/logout/").status_code, 302)

    def test_login_post_enforces_csrf(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/login/", {"username": "buyer", "password": "anything"}
            ).status_code,
            403,
        )

    def test_historical_unit_price_is_preserved(self):
        from meditrack.models import DetailTransaksi
        from meditrack.serializers import DetailTransaksiSerializer

        trx = TransaksiPenjualan.objects.create(user=self.user, status="PAID")
        item = DetailTransaksi.objects.create(
            transaksi=trx, obat=self.obat, jumlah=2, subtotal=20
        )
        self.assertEqual(DetailTransaksiSerializer(item).data["harga_satuan"], "10.00")
