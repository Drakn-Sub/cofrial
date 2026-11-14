from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from oscar.core.loading import get_model

from crm.models import Interaccion
from cuentas.models import Cliente, Perfil
from logistica.alertas import evaluar
from logistica.models import AlertaFrio, Camion, Despacho, DespachoPedido

Order = get_model("order", "Order")
User = get_user_model()


def lectura(camion_id, temp, fuera, hace_segundos):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO logistica.telemetria (registrado_en, camion_id, temp_camara, lat, long, combustible_pct, "
            "alerta_ruptura_frio) VALUES (%s, %s, %s, -38.73, -72.59, 70, %s)",
            [timezone.now() - timedelta(seconds=hace_segundos), camion_id, temp, fuera],
        )


class TorreDeControlTests(TestCase):
    def setUp(self):
        self.camion = Camion.objects.create(camion_id="CF-027", patente="CFR027", capacidad_kg=8000, regimen="REFRIGERADO")

    def test_una_lectura_aislada_no_abre_alerta(self):
        lectura("CF-027", 2.0, False, 60)
        lectura("CF-027", 6.5, True, 10)
        evaluar()
        self.assertFalse(AlertaFrio.objects.exists())

    def test_dos_lecturas_fuera_de_rango_abren_alerta_y_avisan_al_crm(self):
        comprador = User.objects.create_user("compras@h.cl")
        hospital = Cliente.objects.create(tipo="B2B", rut="61.607.900-1", razon_social="Hospital")
        Perfil.objects.filter(usuario=comprador).update(cliente=hospital)
        pedido = Order.objects.create(
            number="100050", user=comprador, currency="CLP", total_incl_tax=1, total_excl_tax=1,
            shipping_incl_tax=0, shipping_excl_tax=0, site_id=1, status="En ruta",
        )
        despacho = Despacho.objects.create(
            camion=self.camion, conductor=comprador, salida_programada=timezone.now(),
            salida_real=timezone.now(), estado="EN_RUTA",
        )
        DespachoPedido.objects.create(despacho=despacho, pedido=pedido)
        lectura("CF-027", 5.1, True, 40)
        lectura("CF-027", 6.8, True, 10)

        self.assertEqual(evaluar(), (1, 0))
        alerta = AlertaFrio.objects.get()
        self.assertEqual(float(alerta.temp_extrema), 6.8)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, "En ruta con alerta")
        self.assertTrue(Interaccion.objects.filter(cliente=hospital, canal="SISTEMA", urgencia_ia="ALTA").exists())

    def test_alerta_se_cierra_cuando_vuelve_el_frio(self):
        lectura("CF-027", 5.1, True, 120)
        lectura("CF-027", 6.8, True, 90)
        evaluar()
        lectura("CF-027", 3.2, False, 40)
        lectura("CF-027", 2.4, False, 10)
        self.assertEqual(evaluar(), (0, 1))
        self.assertIsNotNone(AlertaFrio.objects.get().fin_en)
