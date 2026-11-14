"""CRM propio (esquema crm): embudo comercial B2B e interacciones con clientes."""
from django.conf import settings
from django.db import models
from django.db.models import Q

from cuentas.models import Cliente


class EtapaPipeline(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    orden = models.PositiveSmallIntegerField(unique=True)
    probabilidad_pct = models.PositiveSmallIntegerField()
    es_cierre = models.BooleanField(default=False, help_text="Ganado o Perdido")

    class Meta:
        db_table = 'crm"."etapa_pipeline'
        ordering = ["orden"]
        verbose_name = "etapa del embudo"
        verbose_name_plural = "etapas del embudo"
        constraints = [models.CheckConstraint(condition=Q(probabilidad_pct__lte=100), name="ck_probabilidad")]

    def __str__(self):
        return self.nombre


class Prospecto(models.Model):
    ORIGENES = [("WEB", "Web"), ("REFERIDO", "Referido"), ("LICITACION", "Licitación"), ("FERIA", "Feria")]

    razon_social = models.CharField(max_length=150)
    rut_empresa = models.CharField("RUT empresa", max_length=12, blank=True)
    nombre_contacto = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    origen = models.CharField(max_length=20, choices=ORIGENES)
    cliente = models.OneToOneField(
        Cliente, null=True, blank=True, on_delete=models.SET_NULL, help_text="Se completa al convertirlo en cliente"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm"."prospecto'
        ordering = ["-creado_en"]

    def __str__(self):
        return self.razon_social


class Oportunidad(models.Model):
    prospecto = models.ForeignKey(Prospecto, on_delete=models.PROTECT, related_name="oportunidades")
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="oportunidades")
    etapa = models.ForeignKey(EtapaPipeline, on_delete=models.PROTECT)
    titulo = models.CharField(max_length=120)
    monto_estimado = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    fecha_cierre_est = models.DateField("cierre estimado", null=True, blank=True)
    motivo_perdida = models.CharField(max_length=150, blank=True)
    pedido = models.ForeignKey("order.Order", null=True, blank=True, on_delete=models.SET_NULL)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crm"."oportunidad'
        ordering = ["etapa__orden", "-actualizado_en"]
        verbose_name_plural = "oportunidades"
        constraints = [
            models.CheckConstraint(condition=Q(monto_estimado__isnull=True) | Q(monto_estimado__gte=0), name="ck_monto")
        ]

    def __str__(self):
        return f"{self.titulo} ({self.prospecto})"


class Interaccion(models.Model):
    CANALES = [
        ("PORTAL", "Portal"),
        ("CORREO", "Correo"),
        ("TELEFONO", "Teléfono"),
        ("REUNION", "Reunión"),
        ("SISTEMA", "Sistema"),
    ]
    CATEGORIAS = [
        ("RECLAMO", "Reclamo"),
        ("COTIZACION", "Cotización"),
        ("DESPACHO", "Despacho"),
        ("FACTURACION", "Facturación"),
        ("OTRO", "Otro"),
        ("SIN_CLASIFICAR", "Sin clasificar"),
    ]
    URGENCIAS = [("ALTA", "Alta"), ("MEDIA", "Media"), ("BAJA", "Baja")]

    oportunidad = models.ForeignKey(
        Oportunidad, null=True, blank=True, on_delete=models.CASCADE, related_name="interacciones"
    )
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.CASCADE, related_name="interacciones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    canal = models.CharField(max_length=15, choices=CANALES)
    contenido = models.TextField(max_length=4000)
    categoria_ia = models.CharField("categoría (IA)", max_length=20, choices=CATEGORIAS, default="SIN_CLASIFICAR")
    urgencia_ia = models.CharField("urgencia (IA)", max_length=5, choices=URGENCIAS, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crm"."interaccion'
        ordering = ["-creado_en"]
        verbose_name = "interacción"
        verbose_name_plural = "interacciones"
        constraints = [
            models.CheckConstraint(
                condition=Q(oportunidad__isnull=False) | Q(cliente__isnull=False), name="ck_interaccion_destino"
            )
        ]

    def __str__(self):
        return f"{self.get_canal_display()} · {self.contenido[:50]}"
