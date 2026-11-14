from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from oscar.core.loading import get_class, get_model

from cuentas.models import AuditoriaEvento, Cliente, ListaPrecio, Perfil, PrecioLista

Product = get_model("catalogue", "Product")
ProductClass = get_model("catalogue", "ProductClass")
Partner = get_model("partner", "Partner")
StockRecord = get_model("partner", "StockRecord")
Order = get_model("order", "Order")
Selector = get_class("partner.strategy", "Selector")
User = get_user_model()


def crear_producto(precio=Decimal("8990")):
    clase = ProductClass.objects.create(name="Refrigerado")
    producto = Product.objects.create(title="Posta negra 1 kg", product_class=clase)
    StockRecord.objects.create(
        product=producto, partner=Partner.objects.create(name="Cofrial"),
        partner_sku="CF-1", price=precio, price_currency="CLP", num_in_stock=10,
    )
    return producto


class PreciosConvenioTests(TestCase):
    def setUp(self):
        self.producto = crear_producto()
        self.lista = ListaPrecio.objects.create(nombre="Convenio", vigente_desde=date(2020, 1, 1))
        PrecioLista.objects.create(lista=self.lista, producto=self.producto, precio_neto=Decimal("7990"))
        self.hospital = Cliente.objects.create(tipo="B2B", rut="61.607.900-1", razon_social="Hospital", lista_precio=self.lista)

    def precio_para(self, usuario):
        info = Selector().strategy(user=usuario).fetch_for_product(self.producto)
        return info.price.excl_tax

    def test_publico_general_ve_precio_de_catalogo(self):
        anonimo = type("Anonimo", (), {"is_authenticated": False})()
        self.assertEqual(self.precio_para(anonimo), Decimal("8990"))

    def test_hospital_con_convenio_ve_su_precio(self):
        comprador = User.objects.create_user("compras@h.cl", "compras@h.cl")
        Perfil.objects.filter(usuario=comprador).update(cliente=self.hospital)
        comprador.refresh_from_db()
        self.assertEqual(self.precio_para(comprador), Decimal("7990"))

    def test_convenio_vencido_vuelve_al_precio_publico(self):
        self.lista.vigente_hasta = date(2020, 12, 31)
        self.lista.save()
        comprador = User.objects.create_user("compras@h.cl", "compras@h.cl")
        Perfil.objects.filter(usuario=comprador).update(cliente=self.hospital)
        comprador.refresh_from_db()
        self.assertEqual(self.precio_para(comprador), Decimal("8990"))


class AutorizacionPorObjetoTests(TestCase):
    """IDOR (OWASP A01): un cliente no puede ver el pedido de otro cambiando el número en la URL."""

    def test_pedido_ajeno_responde_404(self):
        dueno = User.objects.create_user("a@demo.cl", "a@demo.cl", "Clave-larga-123!")
        intruso = User.objects.create_user("b@demo.cl", "b@demo.cl", "Clave-larga-123!")
        pedido = Order.objects.create(
            number="100023", user=dueno, currency="CLP", total_incl_tax=1, total_excl_tax=1,
            shipping_incl_tax=0, shipping_excl_tax=0, site_id=1,
        )
        navegador = Client()
        navegador.force_login(dueno)
        self.assertEqual(navegador.get(f"/accounts/orders/{pedido.number}/").status_code, 200)
        navegador.force_login(intruso)
        self.assertEqual(navegador.get(f"/accounts/orders/{pedido.number}/").status_code, 404)


@override_settings(HOST_TIENDA="tienda.cofrial.test", HOST_CRM="crm.cofrial.test", HOST_OPS="ops.cofrial.test",
                   ALLOWED_HOSTS=["tienda.cofrial.test", "crm.cofrial.test", "ops.cofrial.test", "testserver"])
class CanalesPorHostTests(TestCase):
    def test_rutas_internas_no_existen_en_la_tienda(self):
        for ruta in ["/admin/", "/dashboard/", "/crm/", "/ops/"]:
            self.assertEqual(self.client.get(ruta, HTTP_HOST="tienda.cofrial.test").status_code, 404, ruta)

    def test_cada_host_abre_su_canal(self):
        self.assertRedirects(self.client.get("/", HTTP_HOST="crm.cofrial.test"), "/crm/", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/", HTTP_HOST="ops.cofrial.test"), "/ops/", fetch_redirect_response=False)


@override_settings(REQUIERE_2FA=True)
class SegundoFactorTests(TestCase):
    def test_personal_interno_debe_verificar_codigo(self):
        vendedor = User.objects.create_user("v@cofrial.cl", "v@cofrial.cl", is_staff=True)
        self.client.force_login(vendedor)
        respuesta = self.client.get("/crm/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith("/cuentas/2fa/"))

    def test_redireccion_abierta_bloqueada(self):
        vendedor = User.objects.create_user("v@cofrial.cl", "v@cofrial.cl", is_staff=True)
        self.client.force_login(vendedor)
        respuesta = self.client.get("/cuentas/2fa/?next=https://sitio-malicioso.example/")
        self.assertNotContains(respuesta, "sitio-malicioso")


class AuditoriaTests(TestCase):
    def test_login_fallido_queda_registrado_sin_la_clave(self):
        User.objects.create_user("a@demo.cl", "a@demo.cl", "Clave-larga-123!")
        self.client.post("/accounts/login/", {"login-username": "a@demo.cl", "login-password": "incorrecta", "login_submit": "1"})
        evento = AuditoriaEvento.objects.filter(accion="LOGIN_FALLIDO").first()
        self.assertIsNotNone(evento)
        self.assertNotIn("incorrecta", evento.detalle + evento.entidad_id)

    def test_salud_verifica_la_base_de_datos(self):
        self.assertEqual(self.client.get("/salud/").json(), {"estado": "ok"})
