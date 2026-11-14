"""Segundo factor (TOTP) para usuarios internos y chequeo de salud para el balanceador."""
import base64
import io

import qrcode
import qrcode.image.svg
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from .utils import auditar


def _destino_seguro(request):
    """Evita redirecciones abiertas: solo se acepta un destino del mismo sitio."""
    destino = request.POST.get("next") or request.GET.get("next") or "/dashboard/"
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return "/dashboard/"


def _qr_svg(uri):
    imagen = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode()


@never_cache
@login_required(login_url="/accounts/login/")
def segundo_factor(request):
    usuario = request.user
    if not usuario.is_staff:
        return redirect("/")
    if usuario.is_verified():
        return redirect(_destino_seguro(request))

    dispositivo = TOTPDevice.objects.filter(user=usuario, confirmed=True).first()
    registrando = dispositivo is None
    if registrando:
        dispositivo, _ = TOTPDevice.objects.get_or_create(
            user=usuario, confirmed=False, defaults={"name": "Autenticador del teléfono"}
        )

    error = ""
    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip().replace(" ", "")
        if codigo.isdigit() and dispositivo.verify_token(codigo):
            if registrando:
                dispositivo.confirmed = True
                dispositivo.save(update_fields=["confirmed"])
                auditar("2FA_REGISTRADO", request, entidad="usuario", entidad_id=usuario.pk)
            otp_login(request, dispositivo)
            auditar("2FA_OK", request, entidad="usuario", entidad_id=usuario.pk)
            return redirect(_destino_seguro(request))
        auditar("2FA_FALLIDO", request, entidad="usuario", entidad_id=usuario.pk, resultado="RECHAZADO")
        error = "El código no es válido o ya expiró. Usa el código que aparece ahora en tu aplicación."

    contexto = {
        "registrando": registrando,
        "error": error,
        "next": _destino_seguro(request),
        "qr": _qr_svg(dispositivo.config_url) if registrando else None,
    }
    return render(request, "cuentas/segundo_factor.html", contexto)


@require_GET
@never_cache
def salud(request):
    """Chequeo de salud del ALB: responde 200 solo si Django y PostgreSQL funcionan."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"estado": "ok"})
    except Exception:
        return HttpResponse("base de datos no disponible", status=503, content_type="text/plain")
