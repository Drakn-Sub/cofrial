from django.contrib import admin

from .models import AlertaFrio, Camion, CategoriaFrio, Despacho, DespachoPedido


@admin.register(Camion)
class CamionAdmin(admin.ModelAdmin):
    list_display = ("camion_id", "patente", "regimen", "capacidad_kg", "activo")
    list_filter = ("regimen", "activo")
    search_fields = ("camion_id", "patente")


@admin.register(CategoriaFrio)
class CategoriaFrioAdmin(admin.ModelAdmin):
    list_display = ("categoria", "regimen", "temp_min_c", "temp_max_c")


class DespachoPedidoInline(admin.TabularInline):
    model = DespachoPedido
    extra = 1
    raw_id_fields = ("pedido",)


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = ("id", "camion", "conductor", "salida_programada", "salida_real", "estado")
    list_filter = ("estado",)
    inlines = [DespachoPedidoInline]


@admin.register(AlertaFrio)
class AlertaFrioAdmin(admin.ModelAdmin):
    list_display = ("camion", "inicio_en", "fin_en", "temp_extrema", "estado", "atendida_por")
    list_filter = ("estado",)
    readonly_fields = ("camion", "inicio_en", "fin_en", "temp_extrema", "despacho")
