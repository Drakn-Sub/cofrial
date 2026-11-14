"""Clientes, perfiles B2B/B2C, listas de precio y auditoría (MER del informe, esquemas comercial y seguridad)."""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Comuna(models.Model):
    codigo_cut = models.PositiveIntegerField(primary_key=True, help_text="Código Único Territorial (INE)")
    nombre = models.CharField(max_length=60)
    region = models.CharField(max_length=60)
    con_cobertura = models.BooleanField(default=False)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ListaPrecio(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "lista de precios"
        verbose_name_plural = "listas de precios"
        constraints = [
            models.CheckConstraint(
                condition=Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=models.F("vigente_desde")),
                name="ck_lista_vigencia",
            )
        ]

    def __str__(self):
        return self.nombre

    def esta_vigente(self, fecha=None):
        fecha = fecha or timezone.localdate()
        return self.vigente_desde <= fecha and (self.vigente_hasta is None or fecha <= self.vigente_hasta)


class PrecioLista(models.Model):
    lista = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name="precios")
    producto = models.ForeignKey("catalogue.Product", on_delete=models.CASCADE, related_name="precios_convenio")
    precio_neto = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "precio de lista"
        verbose_name_plural = "precios de lista"
        constraints = [
            models.UniqueConstraint(fields=["lista", "producto"], name="uq_lista_producto"),
            models.CheckConstraint(condition=Q(precio_neto__gt=0), name="ck_precio_positivo"),
        ]


class Cliente(models.Model):
    TIPOS = [("B2B", "Institucional (B2B)"), ("B2C", "Público general (B2C)")]
    CONDICIONES = [("CONTADO", "Contado"), ("30_DIAS", "30 días"), ("60_DIAS", "60 días")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=3, choices=TIPOS)
    rut = models.CharField("RUT", max_length=12, unique=True)
    razon_social = models.CharField(max_length=150)
    giro = models.CharField(max_length=120, blank=True)
    comuna = models.ForeignKey(Comuna, null=True, blank=True, on_delete=models.PROTECT)
    lista_precio = models.ForeignKey(ListaPrecio, null=True, blank=True, on_delete=models.PROTECT)
    condicion_pago = models.CharField(max_length=10, choices=CONDICIONES, default="CONTADO")
    consentimiento_datos = models.BooleanField(default=False, help_text="Ley 21.719: consentimiento informado")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["razon_social"]
        constraints = [
            models.CheckConstraint(condition=Q(tipo="B2B") | Q(lista_precio__isnull=True), name="ck_b2c_sin_lista"),
            models.CheckConstraint(condition=Q(tipo__in=["B2B", "B2C"]), name="ck_tipo_cliente"),
        ]

    def __str__(self):
        return f"{self.razon_social} ({self.rut})"


class Perfil(models.Model):
    """Une un usuario de Django con el cliente al que representa (perfil B2B o B2C)."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios")
    cargo = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.usuario} → {self.cliente or 'sin cliente'}"

    @property
    def es_b2b(self):
        return self.cliente is not None and self.cliente.tipo == "B2B"


class AuditoriaEvento(models.Model):
    """Registro de solo inserción: el rol cofrial_app no tiene UPDATE ni DELETE sobre esta tabla."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    accion = models.CharField(max_length=40)
    entidad = models.CharField(max_length=40, blank=True)
    entidad_id = models.CharField(max_length=64, blank=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    resultado = models.CharField(max_length=10, default="OK")
    detalle = models.CharField(max_length=200, blank=True)
    ocurrido_en = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'seguridad"."auditoria_evento'
        ordering = ["-ocurrido_en"]
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"

    def __str__(self):
        return f"{self.ocurrido_en:%Y-%m-%d %H:%M} {self.accion} {self.resultado}"
