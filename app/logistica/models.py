"""Flota, despachos, telemetría y alertas de cadena de frío (esquema logistica)."""
from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Camion(models.Model):
    REGIMENES = [("CONGELADO", "Congelado (−25 a −18 °C)"), ("REFRIGERADO", "Refrigerado (0 a 4 °C)")]

    camion_id = models.CharField(max_length=10, primary_key=True, help_text="Ej.: CF-001")
    patente = models.CharField(max_length=8, unique=True)
    capacidad_kg = models.PositiveIntegerField()
    regimen = models.CharField(max_length=12, choices=REGIMENES)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'logistica"."camion'
        ordering = ["camion_id"]
        verbose_name = "camión"
        verbose_name_plural = "camiones"

    def __str__(self):
        return self.camion_id

    @property
    def rango(self):
        return (-25, -18) if self.regimen == "CONGELADO" else (0, 4)


class CategoriaFrio(models.Model):
    """Rango térmico de cada categoría de Oscar, en una tabla propia 1:1 (no se modifica Oscar)."""

    categoria = models.OneToOneField("catalogue.Category", on_delete=models.CASCADE, primary_key=True)
    regimen = models.CharField(max_length=12, choices=Camion.REGIMENES)
    temp_min_c = models.DecimalField(max_digits=4, decimal_places=1)
    temp_max_c = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        db_table = 'logistica"."categoria_frio'
        verbose_name = "rango térmico de categoría"
        verbose_name_plural = "rangos térmicos de categorías"
        constraints = [models.CheckConstraint(condition=Q(temp_min_c__lt=F("temp_max_c")), name="ck_rango_termico")]


class Despacho(models.Model):
    ESTADOS = [("PROGRAMADO", "Programado"), ("EN_RUTA", "En ruta"), ("CERRADO", "Cerrado")]

    camion = models.ForeignKey(Camion, on_delete=models.PROTECT, related_name="despachos")
    conductor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="despachos")
    salida_programada = models.DateTimeField()
    salida_real = models.DateTimeField(null=True, blank=True)
    llegada_real = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="PROGRAMADO")

    class Meta:
        db_table = 'logistica"."despacho'
        ordering = ["-salida_programada"]
        constraints = [
            models.CheckConstraint(
                condition=Q(llegada_real__isnull=True) | Q(llegada_real__gte=F("salida_real")), name="ck_fechas_despacho"
            )
        ]

    def __str__(self):
        return f"Despacho {self.pk} · {self.camion_id} · {self.get_estado_display()}"


class DespachoPedido(models.Model):
    despacho = models.ForeignKey(Despacho, on_delete=models.CASCADE, related_name="pedidos")
    pedido = models.OneToOneField("order.Order", on_delete=models.PROTECT, related_name="despacho_asignado")

    class Meta:
        db_table = 'logistica"."despacho_pedido'
        verbose_name = "pedido del despacho"
        verbose_name_plural = "pedidos del despacho"


class AlertaFrio(models.Model):
    ESTADOS = [("ABIERTA", "Abierta"), ("EN_GESTION", "En gestión"), ("CERRADA", "Cerrada")]

    camion = models.ForeignKey(Camion, on_delete=models.PROTECT, related_name="alertas")
    despacho = models.ForeignKey(Despacho, null=True, blank=True, on_delete=models.SET_NULL, related_name="alertas")
    inicio_en = models.DateTimeField()
    fin_en = models.DateTimeField(null=True, blank=True)
    temp_extrema = models.DecimalField(max_digits=4, decimal_places=1)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="ABIERTA")
    atendida_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    accion_tomada = models.TextField(blank=True, max_length=2000)

    class Meta:
        db_table = 'logistica"."alerta_frio'
        ordering = ["-inicio_en"]
        verbose_name = "alerta de frío"
        verbose_name_plural = "alertas de frío"
        constraints = [
            models.UniqueConstraint(fields=["camion"], condition=Q(fin_en__isnull=True), name="uq_una_alerta_abierta")
        ]

    def __str__(self):
        return f"Alerta {self.camion_id} {self.inicio_en:%d-%m %H:%M}"


class Telemetria(models.Model):
    """Tabla particionada por mes creada con SQL (migración 0002). Django solo la lee."""

    pk = models.CompositePrimaryKey("telemetria_id", "registrado_en")
    telemetria_id = models.BigIntegerField()
    registrado_en = models.DateTimeField()
    camion = models.ForeignKey(Camion, on_delete=models.DO_NOTHING, db_column="camion_id", db_constraint=False)
    temp_camara = models.DecimalField(max_digits=4, decimal_places=1)
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    long = models.DecimalField(max_digits=9, decimal_places=6)
    combustible_pct = models.SmallIntegerField()
    alerta_ruptura_frio = models.BooleanField()
    recibido_en = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'logistica"."telemetria'
