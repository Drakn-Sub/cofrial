"""Carga datos de demostración idempotentes (se puede ejecutar varias veces).

    python manage.py cargar_demo

Los usuarios de demostración se crean SIN contraseña utilizable. Se les asigna una con
`python manage.py changepassword <correo>`, o definiendo CLAVE_DEMO solo al ejecutar
este comando (la variable nunca se guarda en el repositorio).
"""
import os
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from oscar.core.loading import get_model

from crm.models import EtapaPipeline, Oportunidad, Prospecto
from cuentas.models import Cliente, Comuna, ListaPrecio, Perfil, PrecioLista
from logistica.models import Camion, CategoriaFrio

Category = get_model("catalogue", "Category")
Product = get_model("catalogue", "Product")
ProductClass = get_model("catalogue", "ProductClass")
ProductCategory = get_model("catalogue", "ProductCategory")
Partner = get_model("partner", "Partner")
StockRecord = get_model("partner", "StockRecord")
Country = get_model("address", "Country")
User = get_user_model()

COMUNAS = [
    (9101, "Temuco", True), (9112, "Padre Las Casas", True), (9108, "Lautaro", True),
    (9111, "Nueva Imperial", True), (9120, "Villarrica", True), (9115, "Pucón", False),
    (9201, "Angol", True), (9211, "Victoria", True),
]
# (nombre, categoría, precio público CLP, precio convenio CLP, stock)
PRODUCTOS = [
    ("Posta negra de vacuno 1 kg", "Congelados", 8990, 7990, 420),
    ("Pechuga de pollo deshuesada 1 kg", "Congelados", 5490, 4250, 900),
    ("Merluza austral filete 1 kg", "Congelados", 9890, 8400, 260),
    ("Hamburguesa de vacuno 10 un", "Congelados", 6490, 5300, 500),
    ("Leche entera 1 L", "Refrigerados", 1190, 980, 1500),
    ("Yogur natural 1 kg", "Refrigerados", 2890, 2390, 640),
    ("Queso gauda laminado 500 g", "Refrigerados", 5290, 4490, 380),
    ("Mantequilla con sal 250 g", "Refrigerados", 2590, 2150, 720),
]
ETAPAS = [
    ("Prospecto", 1, 10, False), ("Contactado", 2, 20, False), ("Calificado", 3, 40, False),
    ("Propuesta", 4, 60, False), ("Negociación", 5, 80, False), ("Ganado", 6, 100, True), ("Perdido", 7, 0, True),
]


class Command(BaseCommand):
    help = "Carga datos de demostración de Cofrial"

    @transaction.atomic
    def handle(self, *args, **options):
        clave = os.environ.get("CLAVE_DEMO", "")

        for cut, nombre, cobertura in COMUNAS:
            Comuna.objects.update_or_create(
                codigo_cut=cut, defaults={"nombre": nombre, "region": "Araucanía", "con_cobertura": cobertura}
            )
        Country.objects.filter(iso_3166_1_a2="CL").update(is_shipping_country=True, display_order=1)

        clase, _ = ProductClass.objects.get_or_create(name="Producto refrigerado", defaults={"track_stock": True})
        socio, _ = Partner.objects.get_or_create(name="Cofrial")
        categorias = {}
        for nombre, regimen, minimo, maximo in [("Congelados", "CONGELADO", -25, -18), ("Refrigerados", "REFRIGERADO", 0, 4)]:
            categoria = Category.objects.filter(name=nombre).first() or Category.add_root(name=nombre)
            CategoriaFrio.objects.update_or_create(
                categoria=categoria, defaults={"regimen": regimen, "temp_min_c": minimo, "temp_max_c": maximo}
            )
            categorias[nombre] = categoria

        lista, _ = ListaPrecio.objects.get_or_create(
            nombre="Convenio Hospitales 2026", defaults={"vigente_desde": date(2026, 1, 1), "vigente_hasta": date(2026, 12, 31)}
        )
        for i, (nombre, cat, publico, convenio, stock) in enumerate(PRODUCTOS, start=1):
            producto, _ = Product.objects.get_or_create(
                title=nombre, defaults={"product_class": clase, "structure": "standalone", "is_public": True}
            )
            ProductCategory.objects.get_or_create(product=producto, category=categorias[cat])
            StockRecord.objects.update_or_create(
                product=producto,
                partner=socio,
                defaults={"partner_sku": f"CF-{i:04d}", "price": Decimal(publico), "price_currency": "CLP", "num_in_stock": stock},
            )
            PrecioLista.objects.update_or_create(lista=lista, producto=producto, defaults={"precio_neto": Decimal(convenio)})

        temuco = Comuna.objects.get(codigo_cut=9101)
        hospital, _ = Cliente.objects.update_or_create(
            rut="61.607.900-1",
            defaults={
                "tipo": "B2B", "razon_social": "Hospital Regional de Temuco (demostración)", "giro": "Salud pública",
                "comuna": temuco, "lista_precio": lista, "condicion_pago": "30_DIAS", "consentimiento_datos": True,
            },
        )

        def usuario(correo, nombre, staff=False, grupos=()):
            u, creado = User.objects.get_or_create(
                username=correo, defaults={"email": correo, "first_name": nombre, "is_staff": staff}
            )
            if creado:
                if clave:
                    u.set_password(clave)
                else:
                    u.set_unusable_password()
                u.save()
            for g in grupos:
                u.groups.add(g)
            return u

        vendedores = self._grupo("Vendedores", ["crm"], ["cuentas.view_cliente", "cuentas.view_comuna"])
        despacho = self._grupo("Despacho", ["logistica"], ["order.view_order", "order.change_order"])
        jefatura = self._grupo("Jefatura comercial", ["crm", "cuentas"], [])

        comprador = usuario("compras@hospital-demo.cl", "Compras Hospital")
        Perfil.objects.update_or_create(usuario=comprador, defaults={"cliente": hospital, "cargo": "Jefa de abastecimiento"})
        usuario("cliente@demo.cl", "Cliente B2C")
        vendedor = usuario("vendedor@cofrial.cl", "Vendedora Cofrial", staff=True, grupos=[vendedores])
        usuario("jefatura@cofrial.cl", "Jefatura Comercial", staff=True, grupos=[jefatura, vendedores])
        usuario("despacho@cofrial.cl", "Despachador Cofrial", staff=True, grupos=[despacho])

        etapas = {}
        for nombre, orden, prob, cierre in ETAPAS:
            etapas[nombre], _ = EtapaPipeline.objects.update_or_create(
                nombre=nombre, defaults={"orden": orden, "probabilidad_pct": prob, "es_cierre": cierre}
            )
        oportunidades = [
            ("Clínica Alemana de Temuco", "Suministro mensual de congelados", "Propuesta", 4_800_000),
            ("Junaeb Araucanía", "Licitación de lácteos para colegios", "Negociación", 12_500_000),
            ("Restaurante Lafken", "Proteínas premium para temporada", "Contactado", 1_200_000),
            ("Hospital de Villarrica", "Convenio 2027", "Calificado", 9_300_000),
            ("Casino Dreams Temuco", "Abastecimiento de cocina", "Prospecto", 3_100_000),
        ]
        for razon, titulo, etapa, monto in oportunidades:
            prospecto, _ = Prospecto.objects.get_or_create(
                razon_social=razon, defaults={"nombre_contacto": "Contacto de compras", "origen": "REFERIDO"}
            )
            Oportunidad.objects.get_or_create(
                prospecto=prospecto,
                titulo=titulo,
                defaults={"vendedor": vendedor, "etapa": etapas[etapa], "monto_estimado": Decimal(monto)},
            )

        for n in range(1, 51):
            Camion.objects.update_or_create(
                camion_id=f"CF-{n:03d}",
                defaults={
                    "patente": f"CFR{n:03d}", "capacidad_kg": 8000, "activo": True,
                    "regimen": "CONGELADO" if n % 2 == 0 else "REFRIGERADO",
                },
            )

        self.stdout.write(self.style.SUCCESS(
            "Datos de demostración cargados: 8 productos, 1 hospital con convenio, 5 oportunidades y 50 camiones."
        ))
        if not clave:
            self.stdout.write("Los usuarios de demostración no tienen contraseña: asígnala con `manage.py changepassword <correo>`.")

    def _grupo(self, nombre, apps, extra):
        grupo, _ = Group.objects.get_or_create(name=nombre)
        permisos = list(Permission.objects.filter(content_type__app_label__in=apps))
        for codigo in extra:
            app, codename = codigo.split(".")
            permisos += list(Permission.objects.filter(content_type__app_label=app, codename=codename))
        grupo.permissions.set(permisos)
        return grupo
