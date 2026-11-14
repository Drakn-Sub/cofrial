from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
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
        for host in ["crm.cofrial.test", "ops.cofrial.test"]:
            self.assertRedirects(self.client.get("/", HTTP_HOST=host), "/ingresar/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/ingresar/", HTTP_HOST="tienda.cofrial.test").status_code, 404)


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


class CatalogoTests(TestCase):
    """El listado del catálogo lee desde PostgreSQL (no depende de un índice de búsqueda)."""

    def test_catalogo_muestra_productos_publicos(self):
        crear_producto()
        respuesta = self.client.get("/catalogue/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Posta negra 1 kg")


@override_settings(REQUIERE_2FA=False)
class SeparacionDeRolesTests(TestCase):
    """Cada rol abre solo sus secciones; el menú y la pantalla de inicio salen de la misma tabla."""

    def _persona(self, correo, grupo, apps, extra=()):
        usuario = User.objects.create_user(correo, correo, "Clave-larga-123!", is_staff=True)
        g = Group.objects.create(name=grupo)
        g.permissions.set(Permission.objects.filter(content_type__app_label__in=apps))
        for app, codigo in extra:
            g.permissions.add(Permission.objects.get(content_type__app_label=app, codename=codigo))
        usuario.groups.add(g)
        return usuario

    def setUp(self):
        self.vendedora = self._persona("v@cofrial.cl", "Vendedores", ["crm"])
        self.despacho = self._persona("d@cofrial.cl", "Despacho", ["logistica"], [("order", "view_order")])

    def test_sin_sesion_va_al_ingreso_de_la_intranet(self):
        for ruta in ["/crm/", "/ops/", "/dashboard/", "/admin/"]:
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 302, ruta)
            self.assertTrue(respuesta["Location"].startswith("/ingresar/"), ruta)

    def test_cada_rol_llega_a_su_pantalla_al_ingresar(self):
        for correo, inicio in [("v@cofrial.cl", "/crm/"), ("d@cofrial.cl", "/ops/")]:
            respuesta = self.client.post("/ingresar/", {"username": correo, "password": "Clave-larga-123!"})
            self.assertRedirects(respuesta, inicio, fetch_redirect_response=False)
            self.client.logout()

    def test_vendedora_no_abre_torre_ni_pedidos(self):
        self.client.force_login(self.vendedora)
        self.assertEqual(self.client.get("/crm/").status_code, 200)
        for ruta in ["/ops/", "/dashboard/"]:
            self.assertRedirects(self.client.get(ruta), "/crm/", fetch_redirect_response=False)
        self.assertEqual(self.client.post("/ops/alerta/1/tomar/", {"accion_tomada": "x"}).status_code, 403)
        self.assertTrue(AuditoriaEvento.objects.filter(accion="ACCESO_DENEGADO").exists())

    def test_despacho_no_abre_el_crm(self):
        self.client.force_login(self.despacho)
        self.assertEqual(self.client.get("/ops/").status_code, 200)
        self.assertRedirects(self.client.get("/crm/"), "/ops/", fetch_redirect_response=False)

    def test_el_menu_muestra_solo_lo_permitido(self):
        self.client.force_login(self.vendedora)
        html = self.client.get("/crm/").content.decode()
        self.assertIn("Ventas (CRM)", html)
        self.assertNotIn("Torre de control", html)
        self.assertNotIn(">Administración<", html)

    def test_cliente_de_la_tienda_no_ve_la_intranet(self):
        cliente = User.objects.create_user("c@demo.cl", "c@demo.cl", "Clave-larga-123!")
        self.client.force_login(cliente)
        self.assertEqual(self.client.get("/crm/").status_code, 404)

    def test_administracion_sin_tablas_tecnicas_de_la_tienda(self):
        jefe = User.objects.create_superuser("admin", "a@cofrial.cl", "Clave-larga-123!")
        self.client.force_login(jefe)
        html = self.client.get("/admin/").content.decode()
        self.assertIn("Eventos de auditoría", html)
        self.assertNotIn("/admin/basket/", html)
