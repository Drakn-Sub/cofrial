"""Genera actividad histórica de demostración: ~2 meses de pedidos, despachos, alertas y CRM.

    python manage.py cargar_demo        # primero: catálogo, clientes y camiones
    python manage.py generar_actividad  # después: movimiento para la tienda, la torre y Metabase

Es idempotente: si ya existen pedidos de demostración (número con prefijo D), no hace nada.
Todos los nombres y RUT son ficticios. Los usuarios se crean sin contraseña utilizable.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from oscar.core.loading import get_model

from crm.models import Interaccion
from cuentas.models import Perfil, PrecioLista
from logistica.models import AlertaFrio, Camion, Despacho, DespachoPedido

Order = get_model("order", "Order")
Line = get_model("order", "Line")
StockRecord = get_model("partner", "StockRecord")
User = get_user_model()

DIAS = 60
NOMBRES = [
    ("Camila", "Muñoz"), ("Matías", "González"), ("Valentina", "Rojas"), ("Benjamín", "Díaz"),
    ("Francisca", "Soto"), ("Joaquín", "Contreras"), ("Javiera", "Silva"), ("Tomás", "Martínez"),
    ("Antonia", "Sepúlveda"), ("Vicente", "Morales"), ("Catalina", "Fuentes"), ("Agustín", "Pérez"),
    ("Isidora", "Castillo"), ("Martín", "Huenchumilla"),
]
ACCIONES = [
    "Se contactó al conductor; la puerta de la cámara quedó mal cerrada. Temperatura normalizada.",
    "Falla del equipo de frío. Se trasbordó la carga al camión de respaldo.",
    "Corte de energía del equipo durante la carga. Se reinició y se verificó la mercadería.",
    "Sensor con lectura anómala; se verificó con termómetro manual y la carga estaba en rango.",
    "Ruta con detención prolongada. Se priorizó la entrega y se informó al cliente.",
]
INTERACCIONES = [
    ("CORREO", "COTIZACION", "MEDIA", "Solicitan cotización de 200 kg de pechuga de pollo para el próximo mes."),
    ("TELEFONO", "DESPACHO", "ALTA", "Consultan por el retraso del despacho de hoy; necesitan la leche antes del almuerzo."),
    ("CORREO", "FACTURACION", "BAJA", "Piden reenviar la factura de octubre con la orden de compra correcta."),
    ("REUNION", "COTIZACION", "MEDIA", "Reunión para renovar el convenio 2027 con nuevos productos congelados."),
    ("PORTAL", "RECLAMO", "ALTA", "Reclamo: dos cajas de yogur llegaron con la fecha de vencimiento muy próxima."),
    ("TELEFONO", "OTRO", "BAJA", "Actualizan el contacto de compras y el horario de recepción (8:00 a 11:00)."),
    ("CORREO", "DESPACHO", "MEDIA", "Solicitan cambiar la dirección de entrega del pedido a la bodega norte."),
    ("PORTAL", "COTIZACION", "BAJA", "Consultan precios de berries congelados para la temporada de verano."),
]


class Command(BaseCommand):
    help = "Genera pedidos, despachos, alertas e interacciones históricas de demostración"

    @transaction.atomic
    def handle(self, *args, **options):
        if Order.objects.filter(number__startswith="D").exists():
            self.stdout.write("La actividad de demostración ya existe; no se genera de nuevo.")
            return
        azar = random.Random(2026)
        ahora = timezone.localtime()
        sitio = Site.objects.get_current()
        stock = list(StockRecord.objects.select_related("product", "partner").filter(product__is_public=True))
        if not stock:
            self.stderr.write("Primero ejecuta `manage.py cargar_demo`.")
            return
        convenio = {(p.lista_id, p.producto_id): p.precio_neto for p in PrecioLista.objects.all()}

        b2b = list(Perfil.objects.select_related("usuario", "cliente").filter(cliente__tipo="B2B"))
        b2c = [self._usuario(f"cliente{n:02d}@demo.cl", nombre, apellido) for n, (nombre, apellido) in enumerate(NOMBRES, 1)]
        conductores = [self._usuario(f"conductor{n:02d}@cofrial.cl", "Conductor", f"{n:02d}") for n in range(1, 7)]
        despachador = User.objects.filter(username="despacho@cofrial.cl").first() or conductores[0]

        pedidos_por_dia = {}
        numero = 100000
        for dias_atras in range(DIAS, -1, -1):
            dia = ahora - timedelta(days=dias_atras)
            crecimiento = 1 + (DIAS - dias_atras) / DIAS  # la tienda crece en el período
            fin_de_semana = dia.weekday() >= 5
            cantidad_b2c = azar.randint(1, 3 if not fin_de_semana else 5) + int(azar.random() * crecimiento)
            cantidad_b2b = 0 if fin_de_semana else azar.choice([0, 1, 1, 2])
            if dias_atras <= 1:  # hoy y ayer: más pedidos para que haya camiones en ruta
                cantidad_b2c, cantidad_b2b = cantidad_b2c + 5, 3
            clientes = [("B2C", azar.choice(b2c), None) for _ in range(cantidad_b2c)]
            clientes += [("B2B", p.usuario, p.cliente) for p in azar.sample(b2b, min(cantidad_b2b, len(b2b)))]
            for canal, usuario, cliente in clientes:
                hora = azar.randint(8, 20)
                if dias_atras == 0 and hora > ahora.hour:
                    hora = max(8, ahora.hour - 1)
                fecha = dia.replace(hour=hora, minute=azar.randint(0, 59), second=0, microsecond=0)
                numero += 1
                pedido = self._pedido(azar, f"D{numero}", sitio, usuario, cliente, canal, fecha, stock, convenio, dias_atras)
                pedidos_por_dia.setdefault(dias_atras, []).append(pedido)

        self._despachos(azar, pedidos_por_dia, conductores, ahora)
        alertas = self._alertas(azar, ahora, despachador)
        interacciones = self._interacciones(azar, b2b, despachador, ahora)
        total = sum(len(v) for v in pedidos_por_dia.values())
        self.stdout.write(self.style.SUCCESS(
            f"Actividad generada: {total} pedidos en {DIAS} días, {Despacho.objects.count()} despachos, "
            f"{alertas} alertas históricas y {interacciones} interacciones de CRM."
        ))

    def _usuario(self, correo, nombre, apellido):
        usuario, creado = User.objects.get_or_create(
            username=correo, defaults={"email": correo, "first_name": nombre, "last_name": apellido}
        )
        if creado:
            usuario.set_unusable_password()
            usuario.save()
        return usuario

    def _estado(self, azar, dias_atras):
        if dias_atras >= 3:
            return azar.choices(["Entregado", "Anulado", "Rechazado"], [92, 5, 3])[0]
        if dias_atras == 2:
            return "Entregado"
        if dias_atras == 1:
            return azar.choices(["Entregado", "En ruta", "Asignado"], [25, 55, 20])[0]
        return azar.choices(["Recibido", "Pagado", "En preparación", "En ruta"], [15, 20, 20, 45])[0]

    def _pedido(self, azar, numero, sitio, usuario, cliente, canal, fecha, stock, convenio, dias_atras):
        lineas = azar.sample(stock, azar.randint(4, 8) if canal == "B2B" else azar.randint(1, 4))
        envio = Decimal(0) if canal == "B2B" else Decimal(2990)
        detalle, subtotal = [], Decimal(0)
        for sr in lineas:
            cantidad = azar.randint(6, 40) if canal == "B2B" else azar.randint(1, 3)
            unitario = sr.price
            if cliente is not None and cliente.lista_precio_id:
                unitario = convenio.get((cliente.lista_precio_id, sr.product_id), sr.price)
            detalle.append((sr, cantidad, unitario))
            subtotal += unitario * cantidad
        pedido = Order.objects.create(
            number=numero, site=sitio, user=usuario, currency="CLP", status=self._estado(azar, dias_atras),
            total_incl_tax=subtotal + envio, total_excl_tax=subtotal + envio,
            shipping_incl_tax=envio, shipping_excl_tax=envio, shipping_method="Despacho refrigerado Cofrial",
            shipping_code="cofrial", date_placed=fecha,
        )
        for sr, cantidad, unitario in detalle:
            Line.objects.create(
                order=pedido, partner=sr.partner, partner_name=sr.partner.name, partner_sku=sr.partner_sku,
                stockrecord=sr, product=sr.product, title=sr.product.title, upc=sr.product.upc, quantity=cantidad,
                line_price_incl_tax=unitario * cantidad, line_price_excl_tax=unitario * cantidad,
                line_price_before_discounts_incl_tax=unitario * cantidad,
                line_price_before_discounts_excl_tax=unitario * cantidad,
                unit_price_incl_tax=unitario, unit_price_excl_tax=unitario, num_allocated=cantidad,
            )
        return pedido

    def _despachos(self, azar, pedidos_por_dia, conductores, ahora):
        camiones = list(Camion.objects.order_by("camion_id"))
        # Historial: despachos cerrados de las últimas dos semanas con los pedidos entregados
        for dias_atras in range(14, 0, -1):
            entregados = [p for p in pedidos_por_dia.get(dias_atras, []) if p.status == "Entregado"]
            for i in range(0, len(entregados), 4):
                salida = (ahora - timedelta(days=dias_atras)).replace(hour=9, minute=0, second=0, microsecond=0)
                despacho = Despacho.objects.create(
                    camion=azar.choice(camiones), conductor=azar.choice(conductores), estado="CERRADO",
                    salida_programada=salida, salida_real=salida + timedelta(minutes=azar.randint(0, 25)),
                    llegada_real=salida + timedelta(hours=azar.randint(3, 6)),
                )
                for pedido in entregados[i:i + 4]:
                    DespachoPedido.objects.create(despacho=despacho, pedido=pedido)
        # Hoy: seis camiones en ruta; CF-027 (el de la falla simulada) lleva pedidos de clientes con convenio
        en_ruta = [p for d in (0, 1) for p in pedidos_por_dia.get(d, []) if p.status == "En ruta"]
        en_ruta.sort(key=lambda p: (p.total_incl_tax < 100000, p.number))
        salida = ahora.replace(hour=8, minute=30, second=0, microsecond=0)
        for n, camion_id in enumerate(["CF-027", "CF-004", "CF-011", "CF-018", "CF-033", "CF-042"]):
            despacho = Despacho.objects.create(
                camion_id=camion_id, conductor=conductores[n], estado="EN_RUTA",
                salida_programada=salida, salida_real=salida + timedelta(minutes=5 * n),
            )
            for pedido in en_ruta[n::6]:
                DespachoPedido.objects.create(despacho=despacho, pedido=pedido)

    def _alertas(self, azar, ahora, despachador):
        camiones = list(Camion.objects.all())
        creadas = 0
        for dias_atras in sorted(azar.sample(range(2, 30), 9), reverse=True):
            camion = azar.choice(camiones)
            inicio = (ahora - timedelta(days=dias_atras)).replace(hour=azar.randint(9, 17), minute=azar.randint(0, 59))
            temp = Decimal(str(round(azar.uniform(-14, -9) if camion.regimen == "CONGELADO" else azar.uniform(5.5, 9), 1)))
            AlertaFrio.objects.create(
                camion=camion, inicio_en=inicio, fin_en=inicio + timedelta(minutes=azar.randint(6, 35)),
                temp_extrema=temp, estado="CERRADA", atendida_por=despachador, accion_tomada=azar.choice(ACCIONES),
            )
            creadas += 1
        return creadas

    def _interacciones(self, azar, b2b, usuario, ahora):
        creadas = 0
        for perfil in b2b:
            for canal, categoria, urgencia, texto in azar.sample(INTERACCIONES, 4):
                interaccion = Interaccion.objects.create(
                    cliente=perfil.cliente, usuario=usuario, canal=canal, contenido=texto,
                    categoria_ia=categoria, urgencia_ia=urgencia,
                )
                Interaccion.objects.filter(pk=interaccion.pk).update(
                    creado_en=ahora - timedelta(days=azar.randint(0, 30), hours=azar.randint(0, 9))
                )
                creadas += 1
        return creadas
