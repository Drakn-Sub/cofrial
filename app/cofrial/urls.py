from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from cuentas import views as cuentas_views

from .catalogo import CatalogoView, CategoriaView

admin.site.site_header = "Cofrial · Administración"
admin.site.site_title = "Cofrial"
admin.site.index_title = "Fichas y registros"
admin.site.enable_nav_sidebar = False  # la navegación es el menú lateral de la intranet

# La tienda (django-oscar) registra decenas de tablas técnicas en la administración. Se gestionan
# desde "Pedidos y catálogo"; aquí quedan solo las fichas de Cofrial, los usuarios y la seguridad.
_APPS_EN_ADMIN = {"cuentas", "crm", "logistica", "auth", "axes", "otp_totp"}
for _modelo in list(admin.site._registry):
    if _modelo._meta.app_label not in _APPS_EN_ADMIN:
        admin.site.unregister(_modelo)

urlpatterns = [
    path("salud/", cuentas_views.salud, name="salud"),
    path("ingresar/", cuentas_views.Ingreso.as_view(), name="ingresar"),
    path("cuentas/2fa/", cuentas_views.segundo_factor, name="segundo_factor"),
    path("cuentas/2fa/pedir-qr/", cuentas_views.pedir_qr_nuevo, name="pedir_qr_nuevo"),
    path("cuentas/2fa/otro-celular/", cuentas_views.vincular_otro_celular, name="vincular_otro_celular"),
    path("admin/", admin.site.urls),
    path("crm/", include("crm.urls")),
    path("ops/", include("logistica.urls")),
    # Listado del catálogo desde PostgreSQL (reemplaza el de Haystack; ver cofrial/catalogo.py)
    path("catalogue/", CatalogoView.as_view()),
    re_path(r"^catalogue/category/(?P<category_slug>[\w-]+(/[\w-]+)*)_(?P<pk>\d+)/$", CategoriaView.as_view()),
    path("", include(apps.get_app_config("oscar").urls[0])),  # tienda django-oscar
]

if settings.DEBUG:  # solo en desarrollo local; en AWS las imágenes salen de S3 con URL firmadas
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
