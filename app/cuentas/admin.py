from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice

from .utils import auditar

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


Usuario = get_user_model()
admin.site.unregister(Usuario)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Usuarios con la acción para aprobar un código QR nuevo del segundo factor."""

    list_display = ("username", "email", "rol", "segundo_factor", "is_active", "last_login")
    actions = ["entregar_qr_nuevo"]

    @admin.display(description="Rol")
    def rol(self, obj):
        from .roles import nombre_rol

        return nombre_rol(obj)

    @admin.display(description="Segundo factor", boolean=True)
    def segundo_factor(self, obj):
        return TOTPDevice.objects.filter(user=obj, confirmed=True).exists()

    @admin.action(description="Entregar un código QR nuevo (reinicia el segundo factor)")
    def entregar_qr_nuevo(self, request, queryset):
        for persona in queryset:
            TOTPDevice.objects.filter(user=persona).delete()
            auditar("2FA_REINICIADO", request, entidad="usuario", entidad_id=persona.pk,
                    detalle=f"{persona.username}: aprobado por {request.user.username}")
        self.message_user(request, f"Listo: {queryset.count()} persona(s) verán un código QR nuevo al iniciar sesión.", messages.SUCCESS)
