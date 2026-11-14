from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from crm import ia
from crm.models import EtapaPipeline, Interaccion, Oportunidad, Prospecto
from cuentas.models import Cliente

User = get_user_model()


class SalidaDeIATests(TestCase):
    """OWASP LLM05: la respuesta del modelo nunca se usa sin validarla contra una lista cerrada."""

    def test_respuesta_valida(self):
        self.assertEqual(ia.interpretar('{"categoria": "reclamo", "urgencia": "alta"}'), ("RECLAMO", "ALTA"))

    def test_categoria_inventada_por_inyeccion_se_rechaza(self):
        self.assertEqual(ia.interpretar('{"categoria": "HACKEADO", "urgencia": "ALTA"}'), ia.SIN_CLASIFICAR)

    def test_respuesta_que_no_es_json_se_rechaza(self):
        self.assertEqual(ia.interpretar("Ignoré mis instrucciones: categoría ADMIN"), ia.SIN_CLASIFICAR)

    def test_seudonimizacion(self):
        texto = ia.seudonimizar("Soy 12.345.678-5, escribe a ana@hospital.cl o +56 9 8765 4321</mensaje>")
        self.assertNotIn("12.345.678-5", texto)
        self.assertNotIn("ana@hospital.cl", texto)
        self.assertNotIn("8765", texto)
        self.assertNotIn("</mensaje>", texto)

    @override_settings(IA_API_KEY="clave-de-prueba")
    def test_falla_segura_si_la_api_no_responde(self):
        with mock.patch("crm.ia._llamar_api", side_effect=TimeoutError):
            self.assertEqual(ia.clasificar("El pedido llegó tibio"), ia.SIN_CLASIFICAR)

    @override_settings(IA_API_KEY="clave-de-prueba")
    def test_interaccion_se_clasifica_al_guardarse(self):
        cliente = Cliente.objects.create(tipo="B2C", rut="1-9", razon_social="Cliente")
        with mock.patch("crm.ia._llamar_api", return_value='{"categoria":"RECLAMO","urgencia":"ALTA"}'):
            interaccion = Interaccion.objects.create(cliente=cliente, canal="CORREO", contenido="Llegó tibio")
        self.assertEqual((interaccion.categoria_ia, interaccion.urgencia_ia), ("RECLAMO", "ALTA"))


@override_settings(REQUIERE_2FA=False)
class KanbanAutorizacionTests(TestCase):
    def setUp(self):
        self.etapa1 = EtapaPipeline.objects.create(nombre="Prospecto", orden=1, probabilidad_pct=10)
        self.etapa2 = EtapaPipeline.objects.create(nombre="Propuesta", orden=2, probabilidad_pct=60)
        self.ana = User.objects.create_user("ana@cofrial.cl", is_staff=True)
        self.luis = User.objects.create_user("luis@cofrial.cl", is_staff=True)
        prospecto = Prospecto.objects.create(razon_social="Clínica", nombre_contacto="X", origen="WEB")
        self.oportunidad = Oportunidad.objects.create(prospecto=prospecto, vendedor=self.ana, etapa=self.etapa1, titulo="Congelados")

    def test_vendedor_mueve_su_oportunidad(self):
        self.client.force_login(self.ana)
        self.client.post(f"/crm/oportunidad/{self.oportunidad.pk}/mover/", {"etapa": self.etapa2.pk})
        self.oportunidad.refresh_from_db()
        self.assertEqual(self.oportunidad.etapa, self.etapa2)

    def test_vendedor_no_puede_mover_la_de_otro(self):
        self.client.force_login(self.luis)
        respuesta = self.client.post(f"/crm/oportunidad/{self.oportunidad.pk}/mover/", {"etapa": self.etapa2.pk})
        self.assertEqual(respuesta.status_code, 404)
        self.oportunidad.refresh_from_db()
        self.assertEqual(self.oportunidad.etapa, self.etapa1)

    def test_cliente_externo_no_entra_al_crm(self):
        cliente = User.objects.create_user("compras@hospital.cl")
        self.client.force_login(cliente)
        self.assertEqual(self.client.get("/crm/").status_code, 302)
