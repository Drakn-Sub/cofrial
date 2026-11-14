"""Controles de acceso por canal.

EnrutamientoPorHostMiddleware: cada nombre de host expone solo su canal. Las
rutas internas (Admin, panel de Oscar, CRM y torre de control) no existen en
`tienda.`: así se reduce la superficie de ataque del sitio público.

Requiere2FAMiddleware: todo usuario interno (staff) debe verificar un código
TOTP antes de entrar a una ruta interna (compensa la falta de MFA en la cuenta
de estudiante de AWS: riesgo aceptado R1 del informe).
"""
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect

RUTAS_INTERNAS = ("/admin/", "/dashboard/", "/crm/", "/ops/")
RUTAS_2FA = ("/cuentas/2fa/",)


def _host(request):
    return request.get_host().split(":")[0].lower()


class EnrutamientoPorHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tienda, crm, ops = settings.HOST_TIENDA, settings.HOST_CRM, settings.HOST_OPS
        if tienda:  # solo en AWS, donde cada canal tiene su nombre
            host, ruta = _host(request), request.path
            if host == tienda and ruta.startswith(RUTAS_INTERNAS):
                raise Http404("Ruta no disponible en este sitio")
            if host == crm and ruta == "/":
                return redirect("/crm/")
            if host == ops and ruta == "/":
                return redirect("/ops/")
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
