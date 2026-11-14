from django.apps import apps
from django.contrib import admin
from django.urls import include, path

from cuentas import views as cuentas_views

admin.site.site_header = "Cofrial · Administración"
admin.site.site_title = "Cofrial"

urlpatterns = [
    path("salud/", cuentas_views.salud, name="salud"),
    path("cuentas/2fa/", cuentas_views.segundo_factor, name="segundo_factor"),
    path("admin/", admin.site.urls),
    path("", include(apps.get_app_config("oscar").urls[0])),  # tienda django-oscar
]
