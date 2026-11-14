from django.db.models.signals import pre_save
from django.dispatch import receiver
from oscar.apps.order.signals import order_placed

from cuentas.utils import auditar

from .ia import clasificar
from .models import Interaccion


@receiver(order_placed)
def registrar_pedido_en_crm(sender, order, user=None, **kwargs):
    """Cada pedido web queda en la ficha del cliente: el CRM y la tienda comparten la misma base."""
    perfil = getattr(user, "perfil", None) if user is not None else None
    if perfil is not None and perfil.cliente is not None:
        Interaccion.objects.create(
            cliente=perfil.cliente,
            usuario=user,
            canal="PORTAL",
            contenido=f"Pedido web {order.number} por ${order.total_incl_tax:,.0f} CLP".replace(",", "."),
            categoria_ia="OTRO",
            urgencia_ia="BAJA",
        )
    auditar("PEDIDO_CREADO", usuario=user, entidad="pedido", entidad_id=order.number)


@receiver(pre_save, sender=Interaccion)
def clasificar_interaccion(sender, instance, **kwargs):
    if instance.canal != "SISTEMA" and instance.categoria_ia == "SIN_CLASIFICAR" and instance.contenido:
        instance.categoria_ia, instance.urgencia_ia = clasificar(instance.contenido)
