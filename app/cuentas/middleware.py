"""Controles de acceso por canal.

EnrutamientoPorHostMiddleware: cada nombre de host expone solo su canal. Las
rutas internas (Admin, panel de Oscar, CRM y torre de control) no existen en
`tienda.`: así se reduce la superficie de ataque del sitio público.

Requiere2FAMiddleware: todo usuario interno (staff) debe verificar un código
TOTP antes de entrar a una ruta interna (compensa la falta de MFA en la cuenta
de estudiante de AWS: riesgo aceptado R1 del informe).
"""
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.http import urlencode

from . import roles

RUTAS_INTERNAS = ("/admin/", "/dashboard/", "/crm/", "/ops/")
RUTAS_2FA = ("/cuentas/2fa/",)
INGRESO = "/ingresar/"


def _host(request):
    return request.get_host().split(":")[0].lower()


class EnrutamientoPorHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tienda, crm, ops = settings.HOST_TIENDA, settings.HOST_CRM, settings.HOST_OPS
        if tienda:  # solo en AWS, donde cada canal tiene su nombre
            host, ruta = _host(request), request.path
            if host == tienda and (ruta.startswith(RUTAS_INTERNAS) or ruta == INGRESO):
                raise Http404("Ruta no disponible en este sitio")
            if host in (crm, ops) and ruta == "/accounts/login/":
                return redirect(INGRESO)  # el personal entra por el acceso de la intranet
            if host in (crm, ops) and ruta == "/":
                return redirect(INGRESO)  # con sesión iniciada, el ingreso lleva a la pantalla del rol
        return self.get_response(request)


class Requiere2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            settings.REQUIERE_2FA
            and user is not None
            and user.is_authenticated
            and user.is_staff
            and request.path.startswith(RUTAS_INTERNAS)
            and not user.is_verified()
        ):
            return redirect(f"/cuentas/2fa/?next={request.path}")
        return self.get_response(request)


class AccesoPorRolMiddleware:
    """Cada sección interna exige iniciar sesión y tener el permiso de su rol (ver cuentas/roles.py)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta = request.path
        if not ruta.startswith(RUTAS_INTERNAS):
            return self.get_response(request)
        user = request.user
        if not user.is_authenticated:
            return redirect(f"{INGRESO}?{urlencode({'next': ruta})}")
        if not user.is_staff:
            raise Http404("Ruta no disponible")  # un cliente no debe saber que la intranet existe
        if not roles.puede_abrir(user, ruta):
            from .utils import auditar

            auditar("ACCESO_DENEGADO", request, entidad="ruta", entidad_id=ruta[:60], resultado="DENEGADO")
            inicio = roles.inicio_de(user)
            if request.method == "GET" and not inicio.startswith(ruta[: ruta.index("/", 1) + 1]) and inicio != "/catalogue/":
                messages.warning(request, "Tu perfil no tiene acceso a esa sección. Te llevamos a la tuya.")
                return redirect(inicio)
            return HttpResponseForbidden("Tu perfil no tiene acceso a esta sección.")
        return self.get_response(request)
