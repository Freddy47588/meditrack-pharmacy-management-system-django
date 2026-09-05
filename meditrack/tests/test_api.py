from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from meditrack.models import DetailTransaksi, KategoriObat, Obat, Supplier, TransaksiPenjualan


class APIData(APITestCase):
    """All records are created in Django's isolated test database."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('buyer', password='test-password-123')
        cls.other = get_user_model().objects.create_user('other')
        cls.token = Token.objects.create(user=cls.user)
        cls.kategori = KategoriObat.objects.create(nama_kategori='Analgesik')
        cls.supplier = Supplier.objects.create(
            nama_supplier='Supplier Test', alamat='Jalan Test', no_telepon='021123456'
        )
        cls.obat = Obat.objects.create(
            nama_obat='Paracetamol', kategori=cls.kategori, supplier=cls.supplier,
            harga=Decimal('12500.50'), stok=10,
        )

    def authenticate(self):
        # Exercise real TokenAuthentication, including header parsing.
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def obat_payload(self):
        return dict(nama_obat='Vitamin', kategori=self.kategori.pk,
                    supplier=self.supplier.pk, harga='5000.25', stok=5)


class AuthenticationTests(APIData):
    def test_anonymous_can_read_catalog(self):
        for resource, pk in [('obat', self.obat.pk), ('supplier', self.supplier.pk),
                             ('kategori', self.kategori.pk)]:
            with self.subTest(resource=resource):
                response = self.client.get(f'/api/{resource}/')
                self.assertEqual(response.status_code, 200)
                self.assertIsInstance(response.data, list)
                self.assertEqual(response.data[0]['id'], pk)
                self.assertEqual(self.client.get(f'/api/{resource}/{pk}/').status_code, 200)

    def test_anonymous_cannot_write_catalog(self):
        for resource, pk in [('obat', self.obat.pk), ('supplier', self.supplier.pk),
                             ('kategori', self.kategori.pk)]:
            for method, path in [('post', f'/api/{resource}/'),
                                 ('put', f'/api/{resource}/{pk}/'),
                                 ('patch', f'/api/{resource}/{pk}/'),
                                 ('delete', f'/api/{resource}/{pk}/')]:
                with self.subTest(resource=resource, method=method):
                    response = getattr(self.client, method)(path, {}, format='json')
                    self.assertEqual(response.status_code, 401)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_anonymous_cannot_access_transactions_or_cart(self):
        for path in ['/api/transaksi/', '/api/detail-transaksi/', '/api/transaksi/cart/',
                     '/api/transaksi/my/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
        for path in ['/api/transaksi/', '/api/detail-transaksi/',
                     '/api/transaksi/cart/add/', '/api/transaksi/cart/checkout/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 401)

    def test_invalid_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid-test-token')
        self.assertEqual(self.client.get('/api/transaksi/').status_code, 401)

    def test_register_hashes_password_and_does_not_return_it(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'new-buyer', 'password': 'test-password-456',
            'password2': 'test-password-456',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data), {'id', 'username'})
        user = get_user_model().objects.get(pk=response.data['id'])
        self.assertEqual(user.username, 'new-buyer')
        self.assertTrue(user.check_password('test-password-456'))
        self.assertNotEqual(user.password, 'test-password-456')

    def test_register_rejects_invalid_inputs_without_creating_users(self):
        for username, password, confirmation, field in [
            ('buyer', 'abcdef', 'abcdef', 'username'),
            ('new-buyer', 'abcdef', 'different', 'password2'),
            ('ab', 'abcdef', 'abcdef', 'username'),
            ('new-buyer', '1234', '1234', 'password'),
        ]:
            with self.subTest(field=field, username=username):
                response = self.client.post('/api/auth/register/', {
                    'username': username, 'password': password, 'password2': confirmation,
                }, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_login_token_can_access_protected_endpoint(self):
        response = self.client.post('/api/auth/token/', {
            'username': 'buyer', 'password': 'test-password-123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'token': self.token.key})
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')
        self.assertEqual(self.client.get('/api/transaksi/').status_code, 200)

    def test_login_rejects_wrong_password(self):
        response = self.client.post('/api/auth/token/', {
            'username': 'buyer', 'password': 'wrong-password',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('token', response.data)


class CatalogTests(APIData):
    def setUp(self):
        self.user.is_staff = True
        self.user.save()
        self.authenticate()

    def test_obat_crud_and_response_fields(self):
        response = self.client.post('/api/obat/', self.obat_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        pk = response.data['id']
        self.assertEqual(set(response.data), {
            'id', 'nama_obat', 'kategori', 'supplier', 'harga', 'stok',
            'tanggal_masuk', 'kategori_nama', 'supplier_nama', 'expiry_date', 'minimum_stock', 'stock_status', 'expiry_status',
        })
        self.assertEqual(response.data['kategori_nama'], 'Analgesik')
        self.assertEqual(response.data['supplier_nama'], 'Supplier Test')
        path = f'/api/obat/{pk}/'
        self.assertEqual(self.client.get(path).data, response.data)
        response = self.client.put(path, {
            'nama_obat': 'Vitamin C', 'kategori': self.kategori.pk,
            'supplier': self.supplier.pk, 'harga': '6000.75', 'stok': 7,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(path, {'stok': 8}, format='json')
        self.assertEqual(response.status_code, 200)
        obat = Obat.objects.get(pk=pk)
        self.assertEqual(obat.nama_obat, 'Vitamin C')
        self.assertEqual(obat.harga, Decimal('6000.75'))
        self.assertEqual(obat.stok, 8)
        # Stock audit history protects products from deletion.
        self.assertEqual(self.client.delete(path).status_code, 400)
        self.assertTrue(Obat.objects.filter(pk=pk).exists())

    def test_supplier_and_kategori_crud(self):
        cases = [
            ('supplier', Supplier, {'nama_supplier': 'New', 'alamat': 'Address',
                                    'no_telepon': '012345'}, 'nama_supplier'),
            ('kategori', KategoriObat, {'nama_kategori': 'Vitamin'}, 'nama_kategori'),
        ]
        for resource, model, payload, field in cases:
            with self.subTest(resource=resource):
                response = self.client.post(f'/api/{resource}/', payload, format='json')
                self.assertEqual(response.status_code, 201)
                pk = response.data['id']
                self.assertEqual(response.data, {'id': pk, **payload})
                path = f'/api/{resource}/{pk}/'
                self.assertEqual(self.client.get(path).data, response.data)
                response = self.client.patch(path, {field: 'Updated'}, format='json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(getattr(model.objects.get(pk=pk), field), 'Updated')
                self.assertEqual(self.client.delete(path).status_code, 204)
                self.assertFalse(model.objects.filter(pk=pk).exists())

    def test_obat_rejects_invalid_fields_without_saving(self):
        for field, value in [('stok', -1), ('kategori', 99999), ('supplier', 99999),
                             ('harga', 'not-money'), ('nama_obat', '')]:
            with self.subTest(field=field):
                payload = self.obat_payload()
                payload[field] = value
                response = self.client.post('/api/obat/', payload, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertEqual(Obat.objects.count(), 1)

    def test_obat_search_and_price_ordering(self):
        second = Obat.objects.create(
            nama_obat='Vitamin', kategori=self.kategori, supplier=self.supplier,
            harga='5000.00', stok=3,
        )
        response = self.client.get('/api/obat/', {'search': 'Paracetamol'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [self.obat.pk])
        response = self.client.get('/api/obat/', {'ordering': 'harga'})
        self.assertEqual([row['id'] for row in response.data], [second.pk, self.obat.pk])


class TransactionTests(APIData):
    def setUp(self):
        self.authenticate()

    def add_item(self, jumlah=2):
        response = self.client.post('/api/transaksi/cart/add/', {
            'obat': self.obat.pk, 'jumlah': jumlah, 'subtotal': '0.01',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        return response

    def test_transaction_crud_assigns_current_user_and_ignores_total(self):
        response = self.client.post('/api/transaksi/', {
            'user': self.other.pk, 'total_harga': '999.00',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        pk = response.data['id']
        self.assertEqual(response.data['user'], self.user.pk)
        self.assertEqual(response.data['user_username'], 'buyer')
        self.assertEqual(response.data['total_harga'], '0.00')
        self.assertEqual(response.data['detail'], [])
        self.assertEqual(response.data['status'], 'DRAFT')
        path = f'/api/transaksi/{pk}/'
        self.assertEqual(self.client.get(path).data, response.data)
        response = self.client.patch(path, {'total_harga': '100.00'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_harga'], '0.00')
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertFalse(TransaksiPenjualan.objects.filter(pk=pk).exists())

    def test_other_users_transaction_is_hidden_and_cannot_be_modified(self):
        own = TransaksiPenjualan.objects.create(user=self.user)
        other = TransaksiPenjualan.objects.create(user=self.other, status='PENDING')
        response = self.client.get('/api/transaksi/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [own.pk])
        path = f'/api/transaksi/{other.pk}/'
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.patch(path, {'status': 'PAID'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(path).status_code, 404)
        self.assertEqual(self.client.post(path + 'pay/').status_code, 404)
        other.refresh_from_db()
        self.assertEqual(other.status, 'PENDING')

    def test_cart_is_reused_for_current_user(self):
        TransaksiPenjualan.objects.create(user=self.other)
        first = self.client.get('/api/transaksi/cart/')
        second = self.client.get('/api/transaksi/cart/')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(first.data['user'], self.user.pk)
        self.assertEqual(TransaksiPenjualan.objects.filter(user=self.user).count(), 1)

    def test_add_item_calculates_subtotal_total_and_preserves_stock(self):
        response = self.add_item()
        self.assertEqual(response.data['total_harga'], '25001.00')
        item = response.data['detail'][0]
        self.assertEqual(item['obat'], self.obat.pk)
        self.assertEqual(item['obat_nama'], 'Paracetamol')
        self.assertEqual(item['harga_satuan'], '12500.50')
        self.assertEqual(item['subtotal'], '25001.00')
        self.assertEqual(DetailTransaksi.objects.get(pk=item['id']).subtotal, Decimal('25001.00'))
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_add_item_rejects_insufficient_stock(self):
        response = self.client.post('/api/transaksi/cart/add/', {
            'obat': self.obat.pk, 'jumlah': 11,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('jumlah', response.data)
        self.assertFalse(DetailTransaksi.objects.exists())
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 10)

    def test_checkout_and_pay_flow(self):
        cart = self.add_item()
        response = self.client.post('/api/transaksi/cart/checkout/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertEqual(response.data['total_harga'], '25001.00')
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 8)
        pk = cart.data['id']
        self.assertEqual(TransaksiPenjualan.objects.get(pk=pk).status, 'PENDING')
        response = self.client.post(f'/api/transaksi/{pk}/pay/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TransaksiPenjualan.objects.get(pk=pk).status, 'PAID')
        self.assertEqual(self.client.post(f'/api/transaksi/{pk}/pay/').status_code, 400)
        self.assertEqual(self.client.post('/api/transaksi/cart/checkout/').status_code, 400)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 8)

    def test_checkout_empty_cart_is_rejected(self):
        self.assertEqual(self.client.post('/api/transaksi/cart/checkout/').status_code, 400)
        self.client.get('/api/transaksi/cart/')
        self.assertEqual(self.client.post('/api/transaksi/cart/checkout/').status_code, 400)
        self.assertEqual(TransaksiPenjualan.objects.get(user=self.user).status, 'DRAFT')

    def test_checkout_rechecks_single_item_stock(self):
        self.add_item()
        Obat.objects.filter(pk=self.obat.pk).update(stok=1)
        response = self.client.post('/api/transaksi/cart/checkout/')
        self.assertEqual(response.status_code, 400)
        self.obat.refresh_from_db()
        self.assertEqual(self.obat.stok, 1)
        self.assertEqual(TransaksiPenjualan.objects.get(user=self.user).status, 'DRAFT')

    def test_pay_rejects_non_pending_states(self):
        for state in ['DRAFT', 'PAID', 'CANCELLED']:
            with self.subTest(state=state):
                trx = TransaksiPenjualan.objects.create(user=self.user, status=state)
                self.assertEqual(self.client.post(f'/api/transaksi/{trx.pk}/pay/').status_code, 400)
                trx.refresh_from_db()
                self.assertEqual(trx.status, state)

    def test_order_history_excludes_draft_and_other_users(self):
        TransaksiPenjualan.objects.create(user=self.user)
        own = TransaksiPenjualan.objects.create(user=self.user, status='PAID')
        TransaksiPenjualan.objects.create(user=self.other, status='PAID')
        response = self.client.get('/api/transaksi/my/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [own.pk])

    def test_detail_crud_recalculates_subtotal(self):
        trx = TransaksiPenjualan.objects.create(user=self.user)
        response = self.client.post('/api/detail-transaksi/', {
            'transaksi': trx.pk, 'obat': self.obat.pk, 'jumlah': 2, 'subtotal': '0.01',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['subtotal'], '25001.00')
        pk = response.data['id']
        path = f'/api/detail-transaksi/{pk}/'
        self.assertEqual(self.client.get(path).data, response.data)
        response = self.client.patch(path, {'jumlah': 3}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DetailTransaksi.objects.get(pk=pk).subtotal, Decimal('37501.50'))
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertFalse(DetailTransaksi.objects.filter(pk=pk).exists())

    def test_detail_partial_update_rejects_insufficient_stock(self):
        cart = self.add_item()
        pk = cart.data['detail'][0]['id']
        response = self.client.patch(f'/api/detail-transaksi/{pk}/', {'jumlah': 11}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('jumlah', response.data)
        item = DetailTransaksi.objects.get(pk=pk)
        self.assertEqual(item.jumlah, 2)
        self.assertEqual(item.subtotal, Decimal('25001.00'))

    def test_negative_quantity_is_rejected_on_create_and_update(self):
        response = self.client.post('/api/transaksi/cart/add/', {
            'obat': self.obat.pk, 'jumlah': -1,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('jumlah', response.data)
        self.assertFalse(DetailTransaksi.objects.exists())
        cart = self.add_item()
        pk = cart.data['detail'][0]['id']
        response = self.client.patch(f'/api/detail-transaksi/{pk}/', {'jumlah': -1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('jumlah', response.data)
        self.assertEqual(DetailTransaksi.objects.get(pk=pk).jumlah, 2)
