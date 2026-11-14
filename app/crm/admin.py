from django.contrib import admin, messages
from django.db import transaction

from cuentas.models import Cliente
from cuentas.utils import auditar

from .models import EtapaPipeline, Interaccion, Oportunidad, Prospecto


@admin.register(EtapaPipeline)
class EtapaPipelineAdmin(admin.ModelAdmin):
    list_display = ("orden", "nombre", "probabilidad_pct", "es_cierre")


class OportunidadInline(admin.TabularInline):
    model = Oportunidad
    extra = 0
    fields = ("titulo", "etapa", "vendedor", "monto_estimado", "fecha_cierre_est")


@admin.register(Prospecto)
class ProspectoAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "nombre_contacto", "origen", "cliente", "creado_en")
    list_filter = ("origen",)
    search_fields = ("razon_social", "rut_empresa", "nombre_contacto")
    inlines = [OportunidadInline]
    actions = ["convertir_en_cliente_b2b"]

    @admin.action(description="Convertir en cliente B2B")
    def convertir_en_cliente_b2b(self, request, queryset):
        creados = 0
        for prospecto in queryset.filter(cliente__isnull=True):
            if not prospecto.rut_empresa:
                self.message_user(request, f"{prospecto}: falta el RUT de la empresa.", messages.ERROR)
                continue
            with transaction.atomic():
                cliente, _ = Cliente.objects.get_or_create(
                    rut=prospecto.rut_empresa,
                    defaults={"tipo": "B2B", "razon_social": prospecto.razon_social},
                )
                prospecto.cliente = cliente
                prospecto.save(update_fields=["cliente"])
            auditar("PROSPECTO_CONVERTIDO", request, entidad="cliente", entidad_id=cliente.pk)
            creados += 1
        if creados:
            self.message_user(request, f"{creados} prospecto(s) convertidos en cliente B2B.", messages.SUCCESS)


@admin.register(Oportunidad)
class OportunidadAdmin(admin.ModelAdmin):
    list_display = ("titulo", "prospecto", "etapa", "vendedor", "monto_estimado", "fecha_cierre_est")
    list_filter = ("etapa", "vendedor")
    search_fields = ("titulo", "prospecto__razon_social")
    raw_id_fields = ("pedido",)


@admin.register(Interaccion)
class InteraccionAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "cliente", "canal", "categoria_ia", "urgencia_ia", "resumen")
    list_filter = ("canal", "categoria_ia", "urgencia_ia")
    search_fields = ("contenido", "cliente__razon_social")
    readonly_fields = ("categoria_ia", "urgencia_ia", "creado_en")

    @admin.display(description="contenido")
    def resumen(self, obj):
        return obj.contenido[:80]

    def save_model(self, request, obj, form, change):
        if not obj.usuario_id:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
