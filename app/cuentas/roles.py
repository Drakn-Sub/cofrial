"""Separación de roles de la intranet.

Cada sección exige un permiso de Django. Los permisos se entregan por grupo (Vendedores,
Despacho, Jefatura comercial) en `cargar_demo`; el superusuario es el administrador.
El menú, la página de inicio tras el login y el control de acceso usan esta misma tabla,
así lo que una persona ve en el menú es exactamente lo que puede abrir.
"""

from django.conf import settings

# (prefijo de ruta, permiso requerido, nombre en el menú)
SECCIONES = [
    ("/crm/", "crm.view_oportunidad", "Ventas (CRM)"),
    ("/ops/", "logistica.view_alertafrio", "Torre de control"),
    ("/dashboard/", "order.view_order", "Pedidos y catálogo"),
]
# Fichas de datos dentro de la administración, visibles según el rol
FICHAS = [
    ("/admin/crm/", "crm.view_prospecto", "Prospectos y mensajes"),
    ("/admin/logistica/", "logistica.view_camion", "Camiones y despachos"),
]


def nombre_rol(usuario):
    if usuario.is_superuser:
        return "Administrador"
    grupos = list(usuario.groups.values_list("name", flat=True))
    for nombre in ("Jefatura comercial", "Despacho", "Vendedores"):
        if nombre in grupos:
            return {"Vendedores": "Ventas"}.get(nombre, nombre)
    return "Personal" if usuario.is_staff else "Cliente"


def secciones_de(usuario):
    """Entradas del menú lateral que este usuario puede abrir."""
    if not (usuario.is_authenticated and usuario.is_staff):
        return []
    menu = [(url, nombre) for url, permiso, nombre in SECCIONES if usuario.has_perm(permiso)]
    if usuario.is_superuser:
        menu.append(("/admin/", "Administración"))
    else:
        menu += [(url, nombre) for url, permiso, nombre in FICHAS if usuario.has_perm(permiso)]
    return menu


def inicio_de(usuario):
    """Primera pantalla de cada rol después de iniciar sesión."""
    menu = secciones_de(usuario)
    return menu[0][0] if menu else "/catalogue/"


def puede_abrir(usuario, ruta):
    for prefijo, permiso, _ in SECCIONES:
        if ruta.startswith(prefijo):
            return usuario.has_perm(permiso)
    return True  # /admin/: Django muestra solo los modelos permitidos a cada usuario


def contexto(request):
    """Context processor: menú y rol para todas las pantallas internas."""
    base = {"menu_intranet": [], "rol_intranet": "", "host_tienda": settings.HOST_TIENDA}
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return base
    base["rol_intranet"] = nombre_rol(usuario)
    verificado = not usuario.is_staff or getattr(usuario, "is_verified", lambda: True)()
    if settings.REQUIERE_2FA and not verificado:
        return base  # sin segundo factor todavía no se muestra el menú
    ruta = request.path
    menu = [{"url": url, "nombre": nombre, "activa": ruta.startswith(url)} for url, nombre in secciones_de(usuario)]
    # "/admin/" es prefijo de las fichas: solo una entrada queda marcada (la más específica)
    base["menu_intranet"] = menu
    return base
