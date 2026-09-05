from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from .test_api import APIData
from meditrack.models import DetailTransaksi, TransaksiPenjualan, Obat


class DashboardTests(APIData):
    def setUp(self):
        self.client.force_login(self.user)

    def test_dashboard_auth_and_empty_chart(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['chart_values'], [0] * 7)
        self.assertContains(response, 'Inventory Alerts')
        self.client.logout()
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_paid_kpis_chart_and_top_products_exclude_other_users(self):
        today = timezone.now()
        cases = [(self.user, 'PAID', 0, 100, 2), (self.user, 'PENDING', 0, 300, 3),
                 (self.user, 'PAID', 6, 50, 1), (self.user, 'PAID', 7, 25, 1),
                 (self.other, 'PAID', 0, 900, 9)]
        for owner, state, days, total, quantity in cases:
            trx = TransaksiPenjualan.objects.create(user=owner, status=state, total_harga=total)
            TransaksiPenjualan.objects.filter(pk=trx.pk).update(tanggal=today-timedelta(days=days))
            DetailTransaksi.objects.create(transaksi=trx, obat=self.obat, jumlah=quantity, subtotal=total)
        context = self.client.get('/').context
        self.assertEqual(context['sales_today'], Decimal('100'))
        self.assertEqual(context['transactions_today'], 2)
        self.assertEqual(context['chart_values'], [50, 0, 0, 0, 0, 0, 100])
        self.assertEqual(list(context['top_products'])[0]['quantity'], 4)
        self.assertTrue(all(trx.user_id == self.user.pk for trx in context['recent_transactions']))

    def test_inventory_alert_counts(self):
        self.obat.minimum_stock = 10
        self.obat.expiry_date = timezone.localdate() + timedelta(days=30)
        self.obat.save()
        Obat.objects.create(nama_obat='Expired', kategori=self.kategori, supplier=self.supplier,
                            harga=1, stok=0, expiry_date=timezone.localdate()-timedelta(days=1))
        context = self.client.get('/').context
        for field in ['low_stock', 'out_of_stock', 'near_expiry', 'expired']:
            self.assertEqual(context[field], 1)
        self.assertEqual(len(context['inventory_alerts']), 2)
