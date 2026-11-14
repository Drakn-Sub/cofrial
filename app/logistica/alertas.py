"""Torre de control: apertura y cierre de alertas de ruptura de frío.

Histéresis: se abre una alerta cuando las DOS últimas lecturas de un camión están
fuera de rango y se cierra cuando las dos últimas vuelven al rango. Así una lectura
aislada (ruido del sensor) no genera falsas alarmas.

Al abrir una alerta, el sistema cruza los silos: marca los pedidos que viajan en ese
camión como "En ruta con alerta" y deja una interacción en la ficha CRM del cliente.
"""
import logging

from django.db import connection, transaction
from django.utils import timezone

from crm.models import Interaccion
from cuentas.utils import auditar

from .models import AlertaFrio, Despacho

logger = logging.getLogger(__name__)

ULTIMAS_DOS_LECTURAS = """
    SELECT camion_id,
           bool_and(alerta_ruptura_frio)      AS ambas_fuera,
           bool_and(NOT alerta_ruptura_frio)  AS ambas_dentro,
           max(temp_camara)                   AS temp_max,
           count(*)                           AS lecturas
    FROM (
        SELECT camion_id, alerta_ruptura_frio, temp_camara,
               row_number() OVER (PARTITION BY camion_id ORDER BY registrado_en DESC) AS n
        FROM logistica.telemetria
        WHERE registrado_en > now() - interval '5 minutes'
    ) ultimas
    WHERE n <= 2
    GROUP BY camion_id
"""


def _pedidos_en_ruta(despacho):
    return [dp.pedido for dp in despacho.pedidos.select_related("pedido", "pedido__user__perfil__cliente")]


def _abrir_alerta(camion_id, temp):
    ahora = timezone.now()
    despacho = Despacho.objects.filter(camion_id=camion_id, estado="EN_RUTA").first()
    alerta = AlertaFrio.objects.create(camion_id=camion_id, despacho=despacho, inicio_en=ahora, temp_extrema=temp)
    afectados = 0
    if despacho is not None:
        for pedido in _pedidos_en_ruta(despacho):
            if pedido.status == "En ruta":
                pedido.set_status("En ruta con alerta")
                afectados += 1
            cliente = getattr(getattr(pedido.user, "perfil", None), "cliente", None) if pedido.user else None
            if cliente is not None:
                Interaccion.objects.create(
                    cliente=cliente,
                    canal="SISTEMA",
                    categoria_ia="DESPACHO",
                    urgencia_ia="ALTA",
                    contenido=(
                        f"Alerta de cadena de frío en el camión {camion_id} ({temp} °C) "
                        f"que transporta el pedido {pedido.number}. El despachador fue notificado."
                    ),
                )
    auditar("ALERTA_ABIERTA", entidad="camion", entidad_id=camion_id, detalle=f"{temp} C, pedidos {afectados}")
    return alerta


def evaluar():
    """Un ciclo de evaluación. Devuelve (abiertas, cerradas)."""
    with connection.cursor() as cursor:
        cursor.execute(ULTIMAS_DOS_LECTURAS)
        filas = cursor.fetchall()

    abiertas = cerradas = 0
    for camion_id, ambas_fuera, ambas_dentro, temp_max, lecturas in filas:
        with transaction.atomic():
            alerta = AlertaFrio.objects.select_for_update().filter(camion_id=camion_id, fin_en__isnull=True).first()
            if alerta is None and ambas_fuera and lecturas == 2:
                _abrir_alerta(camion_id, temp_max)
                abiertas += 1
            elif alerta is not None and ambas_fuera and temp_max > alerta.temp_extrema:
                alerta.temp_extrema = temp_max
                alerta.save(update_fields=["temp_extrema"])
            elif alerta is not None and ambas_dentro and lecturas == 2:
                alerta.fin_en = timezone.now()
                if alerta.estado == "ABIERTA":
                    alerta.estado = "CERRADA"
                alerta.save(update_fields=["fin_en", "estado"])
                auditar("ALERTA_FIN_EXCURSION", entidad="camion", entidad_id=camion_id)
                cerradas += 1
    return abiertas, cerradas
