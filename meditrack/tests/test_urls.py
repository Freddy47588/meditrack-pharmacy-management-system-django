from django.test import SimpleTestCase
from django.urls import resolve, reverse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from meditrack.auth_api import RegisterAPIView
from meditrack.views import (
    DetailTransaksiViewSet, HomeView, KategoriViewSet, ObatListView,
    ObatViewSet, SupplierViewSet, TransaksiViewSet,
)


class URLTests(SimpleTestCase):
    def test_api_crud_routes_resolve_to_correct_viewsets(self):
        # Literal paths avoid the existing duplicate HTML/API URL names.
        for resource, view in [('obat', ObatViewSet), ('supplier', SupplierViewSet),
                               ('kategori', KategoriViewSet), ('transaksi', TransaksiViewSet),
                               ('detail-transaksi', DetailTransaksiViewSet)]:
            with self.subTest(resource=resource):
                match = resolve(f'/api/{resource}/')
                self.assertIs(match.func.cls, view)
                self.assertEqual(match.func.actions['get'], 'list')
                self.assertEqual(match.func.actions['post'], 'create')
                match = resolve(f'/api/{resource}/1/')
                self.assertIs(match.func.cls, view)
                self.assertEqual(match.func.actions['get'], 'retrieve')
                self.assertEqual(match.func.actions['patch'], 'partial_update')
                self.assertEqual(match.func.actions['delete'], 'destroy')

    def test_cart_checkout_pay_and_history_routes(self):
        for path, method, action in [
            ('cart/', 'get', 'cart'), ('cart/add/', 'post', 'cart_add'),
            ('cart/checkout/', 'post', 'cart_checkout'), ('1/pay/', 'post', 'pay'),
            ('my/', 'get', 'my_orders'),
        ]:
            with self.subTest(path=path):
                match = resolve('/api/transaksi/' + path)
                self.assertIs(match.func.cls, TransaksiViewSet)
                self.assertEqual(match.func.actions[method], action)

    def test_auth_and_documentation_routes(self):
        for name, path, view in [
            ('api-register', '/api/auth/register/', RegisterAPIView),
            ('schema', '/api/schema/', SpectacularAPIView),
            ('swagger-ui', '/api/docs/', SpectacularSwaggerView),
        ]:
            with self.subTest(name=name):
                self.assertEqual(reverse(name), path)
                self.assertIs(resolve(path).func.cls, view)
        self.assertEqual(reverse('api-token'), '/api/auth/token/')
        self.assertEqual(resolve('/api/auth/token/').url_name, 'api-token')

    def test_legacy_routes(self):
        self.assertIs(resolve('/').func.view_class, HomeView)
        self.assertIs(resolve('/obat/').func.view_class, ObatListView)

    def test_swagger_ui_is_public_and_renders_schema_link(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'drf_spectacular/swagger_ui.html')
        self.assertContains(response, '/api/schema/')
