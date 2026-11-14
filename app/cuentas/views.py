"""Segundo factor (TOTP) para usuarios internos y chequeo de salud para el balanceador."""
import base64
import io

import qrcode
import qrcode.image.svg
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from . import roles
from .models import AuditoriaEvento
from .utils import auditar


def _destino_seguro(request):
    """Evita redirecciones abiertas: solo se acepta un destino del mismo sitio.
    Sin destino, cada persona llega a la primera pantalla de su rol."""
    destino = request.POST.get("next") or request.GET.get("next") or ""
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return roles.inicio_de(request.user)


class Ingreso(LoginView):
    """Acceso único del personal a la intranet. Tras la contraseña viene el segundo factor."""

    template_name = "interno/ingreso.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return roles.inicio_de(self.request.user)


def _qr_svg(uri):
    imagen = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode()


@never_cache
@login_required(login_url="/ingresar/")
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


@never_cache
@login_required(login_url="/ingresar/")
def vincular_otro_celular(request):
    """Cambio de celular: borra el segundo factor actual para escanear un código QR nuevo.

    Solo lo puede hacer la propia persona y solo con la sesión ya verificada con el celular
    actual; quien robó una contraseña no puede usar esto para saltarse el segundo factor.
    Si el celular se perdió, lo reinicia el administrador (comando reiniciar_2fa)."""
    usuario = request.user
    if not usuario.is_staff:
        return redirect("/")
    if not usuario.is_verified():
        return redirect("/cuentas/2fa/")
    if request.method == "POST":
        TOTPDevice.objects.filter(user=usuario).delete()
        auditar("2FA_REINICIADO", request, entidad="usuario", entidad_id=usuario.pk, detalle="por la propia persona")
        return redirect("/cuentas/2fa/")
    return render(request, "cuentas/vincular_otro_celular.html")


@never_cache
@require_POST
@login_required(login_url="/ingresar/")
def pedir_qr_nuevo(request):
    """La persona no tiene su celular: deja una solicitud para que el administrador le entregue un QR nuevo.

    No se entrega el QR en el acto: con solo la contraseña, eso anularía el segundo factor.
    El administrador aprueba en Administración → Usuarios (acción "Entregar un código QR nuevo")."""
    usuario = request.user
    if not usuario.is_staff:
        return redirect("/")
    if usuario.is_verified():
        return redirect("/cuentas/2fa/otro-celular/")
    hace_una_hora = timezone.now() - timedelta(hours=1)
    if not AuditoriaEvento.objects.filter(usuario=usuario, accion="2FA_SOLICITUD", ocurrido_en__gte=hace_una_hora).exists():
        auditar("2FA_SOLICITUD", request, entidad="usuario", entidad_id=usuario.pk, resultado="PENDIENTE",
                detalle=f"{usuario.username} pide un código QR nuevo")
    messages.success(request, "Solicitud enviada. Cuando el administrador la apruebe, al iniciar sesión verás un código QR nuevo.")
    return redirect("/cuentas/2fa/")


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
