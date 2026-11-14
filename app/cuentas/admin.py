from django.contrib import admin

from .models import AuditoriaEvento, Cliente, Comuna, ListaPrecio, Perfil, PrecioLista


@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "region", "con_cobertura")
    list_filter = ("con_cobertura", "region")
    search_fields = ("nombre",)


class PrecioListaInline(admin.TabularInline):
    model = PrecioLista
    extra = 1
    raw_id_fields = ("producto",)


@admin.register(ListaPrecio)
class ListaPrecioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "vigente_desde", "vigente_hasta")
    inlines = [PrecioListaInline]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "rut", "tipo", "lista_precio", "condicion_pago", "comuna")
    list_filter = ("tipo", "condicion_pago")
    search_fields = ("razon_social", "rut")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("usuario", "cliente", "cargo")
    search_fields = ("usuario__email", "cliente__razon_social")
    autocomplete_fields = ("cliente",)


@admin.register(AuditoriaEvento)
class AuditoriaEventoAdmin(admin.ModelAdmin):
    """Solo lectura: la auditoría no se edita ni se borra (la base de datos tampoco lo permite)."""

    list_display = ("ocurrido_en", "accion", "resultado", "usuario", "entidad", "entidad_id", "ip_origen")
    list_filter = ("accion", "resultado")
    search_fields = ("entidad_id", "usuario__email", "ip_origen")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
