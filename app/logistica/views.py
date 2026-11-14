"""Torre de control del despachador (Wireframe 5 del informe)."""
import math

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cuentas.utils import auditar

from .models import AlertaFrio

ULTIMA_POSICION = """
    SELECT DISTINCT ON (t.camion_id) t.camion_id, c.regimen, t.registrado_en, t.temp_camara,
           t.lat, t.long, t.combustible_pct, t.alerta_ruptura_frio, t.lat_anterior, t.long_anterior
    FROM (
        SELECT *, lag(lat) OVER w AS lat_anterior, lag(long) OVER w AS long_anterior
        FROM logistica.telemetria
        WHERE registrado_en > now() - interval '10 minutes'
        WINDOW w AS (PARTITION BY camion_id ORDER BY registrado_en)
    ) t
    JOIN logistica.camion c ON c.camion_id = t.camion_id
    ORDER BY t.camion_id, t.registrado_en DESC
"""


# Escala del termómetro de cada régimen: (mínimo y máximo de la escala, rango permitido)
ESCALAS = {
    "CONGELADO": (-30.0, -10.0, -25.0, -18.0),
    "REFRIGERADO": (-4.0, 10.0, 0.0, 4.0),
}


def _porcentaje(valor, bajo, alto):
    return round(max(0.0, min(100.0, (valor - bajo) / (alto - bajo) * 100)), 1)


def _termometro(camion):
    bajo, alto, desde, hasta = ESCALAS.get(camion["regimen"], ESCALAS["REFRIGERADO"])
    temp = float(camion["temp_camara"])
    return {
        "marca": _porcentaje(temp, bajo, alto),
        "rango_inicio": _porcentaje(desde, bajo, alto),
        "rango_ancho": round(_porcentaje(hasta, bajo, alto) - _porcentaje(desde, bajo, alto), 1),
        "rango_texto": f"{desde:g} a {hasta:g} °C",
    }


def _rumbo(camion):
    """Rumbo en grados (0 = norte) entre las dos últimas lecturas, para orientar el camión en el mapa 3D."""
    if camion["lat_anterior"] is None:
        return 0.0
    y1, x1 = math.radians(float(camion["lat_anterior"])), math.radians(float(camion["long_anterior"]))
    y2, x2 = math.radians(float(camion["lat"])), math.radians(float(camion["long"]))
    dx = math.sin(x2 - x1) * math.cos(y2)
    dy = math.cos(y1) * math.sin(y2) - math.sin(y1) * math.cos(y2) * math.cos(x2 - x1)
    return round((math.degrees(math.atan2(dx, dy)) + 360) % 360, 1)


def _ultima_posicion():
    with connection.cursor() as cursor:
        cursor.execute(ULTIMA_POSICION)
        columnas = [c[0] for c in cursor.description]
        flota = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    for camion in flota:
        camion["termometro"] = _termometro(camion)
        camion["rumbo"] = _rumbo(camion)
    # Primero los camiones fuera de rango: es lo que el despachador debe ver de inmediato
    return sorted(flota, key=lambda c: (not c["alerta_ruptura_frio"], c["camion_id"]))


@staff_member_required(login_url="/ingresar/")
def torre_control(request):
    flota = _ultima_posicion()
    activas = (
        AlertaFrio.objects.exclude(estado="CERRADA")
        .select_related("camion", "atendida_por", "despacho")
        .prefetch_related("despacho__pedidos__pedido")
    )
    contexto = {
        "activas": activas,
        "flota": flota,
        "fuera_de_rango": sum(1 for c in flota if c["alerta_ruptura_frio"]),
        # Datos del mapa: se entregan con json_script (escapado), nunca interpolados en JavaScript
        "puntos": [
            {"id": c["camion_id"], "lat": float(c["lat"]), "lon": float(c["long"]), "temp": float(c["temp_camara"]),
             "regimen": c["regimen"], "alerta": bool(c["alerta_ruptura_frio"]), "rumbo": c["rumbo"]}
            for c in flota
        ],
        # Token público de Mapbox (pk.), restringido en Mapbox a nuestro dominio. Sin token, mapa 2D.
        "mapbox_token": settings.MAPBOX_TOKEN,
        "recientes": AlertaFrio.objects.filter(estado="CERRADA").select_related("atendida_por")[:10],
    }
    return render(request, "logistica/torre_control.html", contexto)


@require_POST
@staff_member_required(login_url="/ingresar/")
def tomar_alerta(request, pk):
    alerta = get_object_or_404(AlertaFrio.objects.exclude(estado="CERRADA"), pk=pk)
    accion = request.POST.get("accion_tomada", "").strip()[:2000]
    if not accion:
        messages.error(request, "Describe la acción tomada antes de registrar la alerta.")
        return redirect("logistica:torre")
    alerta.atendida_por = request.user
    alerta.accion_tomada = accion
    alerta.estado = "CERRADA" if alerta.fin_en else "EN_GESTION"
    alerta.save(update_fields=["atendida_por", "accion_tomada", "estado"])
    auditar("ALERTA_GESTIONADA", request, entidad="alerta", entidad_id=alerta.pk, detalle=accion[:120])
    messages.success(request, f"Alerta del camión {alerta.camion_id} registrada a tu nombre.")
    return redirect("logistica:torre")
