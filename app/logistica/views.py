"""Torre de control del despachador (Wireframe 5 del informe)."""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cuentas.utils import auditar

from .models import AlertaFrio

ULTIMA_POSICION = """
    SELECT DISTINCT ON (t.camion_id) t.camion_id, c.regimen, t.registrado_en, t.temp_camara,
           t.lat, t.long, t.combustible_pct, t.alerta_ruptura_frio
    FROM logistica.telemetria t
    JOIN logistica.camion c ON c.camion_id = t.camion_id
    WHERE t.registrado_en > now() - interval '10 minutes'
    ORDER BY t.camion_id, t.registrado_en DESC
"""


def _ultima_posicion():
    with connection.cursor() as cursor:
        cursor.execute(ULTIMA_POSICION)
        columnas = [c[0] for c in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


@staff_member_required(login_url="/accounts/login/")
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
             "regimen": c["regimen"], "alerta": bool(c["alerta_ruptura_frio"])}
            for c in flota
        ],
        "recientes": AlertaFrio.objects.filter(estado="CERRADA").select_related("atendida_por")[:10],
    }
    return render(request, "logistica/torre_control.html", contexto)


@require_POST
@staff_member_required(login_url="/accounts/login/")
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
