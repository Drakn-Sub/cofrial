"""Tablero kanban del vendedor (Wireframe 4 del informe)."""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cuentas.utils import auditar

from .models import EtapaPipeline, Interaccion, Oportunidad


def _oportunidades_visibles(usuario):
    """Autorización por objeto: un vendedor solo ve y mueve sus oportunidades."""
    qs = Oportunidad.objects.select_related("prospecto", "etapa", "vendedor")
    if usuario.is_superuser or usuario.groups.filter(name="Jefatura comercial").exists():
        return qs
    return qs.filter(vendedor=usuario)


@staff_member_required(login_url="/accounts/login/")
def kanban(request):
    visibles = _oportunidades_visibles(request.user)
    etapas = EtapaPipeline.objects.prefetch_related(
        Prefetch("oportunidad_set", queryset=visibles, to_attr="tarjetas")
    )
    resumen = visibles.exclude(etapa__es_cierre=True).aggregate(total=Sum("monto_estimado"), cantidad=Count("id"))
    urgentes = (
        Interaccion.objects.filter(urgencia_ia="ALTA", categoria_ia="RECLAMO")
        .select_related("cliente")
        .order_by("-creado_en")[:8]
    )
    return render(
        request,
        "crm/kanban.html",
        {"etapas": etapas, "todas_las_etapas": EtapaPipeline.objects.all(), "resumen": resumen, "urgentes": urgentes},
    )


@require_POST
@staff_member_required(login_url="/accounts/login/")
def mover(request, pk):
    oportunidad = get_object_or_404(_oportunidades_visibles(request.user), pk=pk)  # 404 si no es suya
    etapa = get_object_or_404(EtapaPipeline, pk=request.POST.get("etapa"))
    anterior = oportunidad.etapa
    oportunidad.etapa = etapa
    oportunidad.save(update_fields=["etapa", "actualizado_en"])
    auditar(
        "OPORTUNIDAD_ETAPA",
        request,
        entidad="oportunidad",
        entidad_id=oportunidad.pk,
        detalle=f"{anterior} -> {etapa}",
    )
    messages.success(request, f"«{oportunidad.titulo}» pasó a {etapa}.")
    return redirect("crm:kanban")
