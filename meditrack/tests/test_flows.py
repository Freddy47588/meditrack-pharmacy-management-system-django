from decimal import Decimal

from meditrack.models import DetailTransaksi, Obat, TransaksiPenjualan

from .test_api import APIData


class FlowRegressionTests(APIData):
    def setUp(self):
        self.authenticate()

    def add(self, quantity=2):
        return self.client.post(
            "/api/transaksi/cart/add/",
            {"obat": self.obat.pk, "jumlah": quantity},
            format="json",
        )

    def test_multipart_cart_add_preserves_form_input_contract(self):
        response = self.client.post(
            "/api/transaksi/cart/add/",
            {"obat": self.obat.pk, "jumlah": 2},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["total_harga"], "25001.00")

    def test_legacy_multiple_drafts_checkout_the_cart_that_was_returned(self):
        data = self.add().data
        newer = TransaksiPenjualan.objects.create(user=self.user)
        self.assertEqual(self.client.get("/api/transaksi/cart/").data["id"], data["id"])
        response = self.client.post("/api/transaksi/cart/checkout/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], data["id"])
        newer.refresh_from_db()
        self.assertEqual(newer.status, "DRAFT")

    def test_patch_and_delete_share_cart_route(self):
        item = self.add().data["detail"][0]
        path = f"/api/transaksi/cart/items/{item['id']}/"
        response = self.client.patch(path, {"jumlah": 3}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_harga"], "37501.50")
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_harga"], "0.00")

    def test_duplicate_add_merges_and_validates_combined_stock(self):
        self.add(6)
        self.assertEqual(self.add(5).status_code, 400)
        self.assertEqual(self.add(4).status_code, 201)
        self.assertEqual(DetailTransaksi.objects.get().jumlah, 10)
        self.assertEqual(
            self.client.post("/api/transaksi/cart/checkout/").status_code, 200
        )
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 0)

    def test_zero_quantity_rejected(self):
        self.assertEqual(self.add(0).status_code, 400)
        self.assertFalse(DetailTransaksi.objects.exists())

    def test_detail_and_cart_ownership_all_methods(self):
        trx = TransaksiPenjualan.objects.create(user=self.other)
        item = DetailTransaksi.objects.create(
            transaksi=trx, obat=self.obat, jumlah=1, subtotal=self.obat.harga
        )
        self.assertEqual(self.client.get("/api/detail-transaksi/").data, [])
        for prefix in ["/api/detail-transaksi/", "/api/transaksi/cart/items/"]:
            for method in ["patch", "delete"]:
                self.assertEqual(
                    getattr(self.client, method)(
                        f"{prefix}{item.pk}/", {}, format="json"
                    ).status_code,
                    404,
                )
        self.assertEqual(
            self.client.get(f"/api/detail-transaksi/{item.pk}/").status_code, 404
        )
        self.assertEqual(
            self.client.post(
                "/api/detail-transaksi/",
                {"transaksi": trx.pk, "obat": self.obat.pk, "jumlah": 1},
                format="json",
            ).status_code,
            400,
        )

    def test_checkout_rolls_back_earlier_item(self):
        self.add()
        second = Obat.objects.create(
            nama_obat="Second",
            kategori=self.kategori,
            supplier=self.supplier,
            harga=1,
            stok=2,
        )
        self.client.post(
            "/api/transaksi/cart/add/", {"obat": second.pk, "jumlah": 2}, format="json"
        )
        second.stok = 0
        second.save()
        self.assertEqual(
            self.client.post("/api/transaksi/cart/checkout/").status_code, 400
        )
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)
        self.assertEqual(TransaksiPenjualan.objects.get().status, "DRAFT")

    def test_paid_transaction_and_detail_cannot_be_edited_or_deleted(self):
        data = self.add().data
        pk, item = data["id"], data["detail"][0]["id"]
        self.client.post("/api/transaksi/cart/checkout/")
        self.client.post(f"/api/transaksi/{pk}/pay/")
        for path in [f"/api/transaksi/{pk}/", f"/api/detail-transaksi/{item}/"]:
            self.assertEqual(
                self.client.patch(path, {"jumlah": 1}, format="json").status_code, 400
            )
            self.assertEqual(self.client.delete(path).status_code, 400)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 8)

    def test_status_cannot_bypass_checkout(self):
        data = self.add().data
        response = self.client.patch(
            f"/api/transaksi/{data['id']}/", {"status": "PAID"}, format="json"
        )
        self.assertEqual(response.data["status"], "DRAFT")

    def test_nonstaff_cannot_manage_catalog(self):
        self.assertEqual(
            self.client.patch(
                f"/api/obat/{self.obat.pk}/", {"stok": 100}, format="json"
            ).status_code,
            403,
        )

    def test_detail_total_and_transfer_protection(self):
        data = self.add().data
        trx = TransaksiPenjualan.objects.create(user=self.other)
        pk = data["detail"][0]["id"]
        self.assertEqual(
            self.client.patch(
                f"/api/detail-transaksi/{pk}/", {"transaksi": trx.pk}, format="json"
            ).status_code,
            400,
        )
        self.client.patch(f"/api/detail-transaksi/{pk}/", {"jumlah": 4}, format="json")
        self.assertEqual(
            TransaksiPenjualan.objects.get(pk=data["id"]).total_harga,
            Decimal("50002.00"),
        )


class KasirTests(APIData):
    def setUp(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def payload(self, quantity=2):
        return {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-obat": self.obat.pk,
            "form-0-jumlah": quantity,
        }

    def test_kasir_success_and_payment(self):
        self.assertEqual(self.client.get("/kasir/").status_code, 200)
        response = self.client.post("/kasir/", self.payload())
        self.assertEqual(response.status_code, 302)
        trx = TransaksiPenjualan.objects.get()
        self.assertEqual(trx.user, self.user)
        self.assertEqual(trx.status, "PENDING")
        self.assertEqual(trx.total_harga, Decimal("25001.00"))
        self.client.post(f"/transaksi/{trx.pk}/pay/")
        trx.refresh_from_db()
        self.assertEqual(trx.status, "PAID")

    def test_kasir_insufficient_stock_and_empty_submission(self):
        for quantity in [11, 0, -1, ""]:
            self.assertEqual(
                self.client.post("/kasir/", self.payload(quantity)).status_code, 200
            )
            self.assertFalse(TransaksiPenjualan.objects.exists())
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_kasir_rolls_back_duplicate_over_stock(self):
        data = {
            **self.payload(6),
            "form-TOTAL_FORMS": "2",
            "form-1-obat": self.obat.pk,
            "form-1-jumlah": 6,
        }
        self.client.post("/kasir/", data)
        self.assertFalse(TransaksiPenjualan.objects.exists())
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_html_ownership_and_draft_delete_does_not_restock(self):
        other = TransaksiPenjualan.objects.create(user=self.other)
        self.assertEqual(self.client.get(f"/transaksi/{other.pk}/").status_code, 404)
        self.assertEqual(
            self.client.post(f"/transaksi/{other.pk}/hapus/").status_code, 404
        )
        trx = TransaksiPenjualan.objects.create(user=self.user)
        DetailTransaksi.objects.create(
            transaksi=trx, obat=self.obat, jumlah=2, subtotal=1
        )
        self.client.post(f"/transaksi/{trx.pk}/hapus/")
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_kasir_requires_staff_and_add_redirects(self):
        self.assertRedirects(self.client.get("/transaksi/tambah/"), "/kasir/")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/kasir/").status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/kasir/").status_code, 302)
