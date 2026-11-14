"""Estrategia de precios de Cofrial.

Oscar llama a `Selector.strategy()` en cada solicitud. Así el precio siempre lo
calcula el servidor según quién compra: un hospital con convenio ve su lista de
precios B2B y el público general ve el precio de catálogo. El navegador solo
envía producto y cantidad, nunca el precio (control de manipulación, STRIDE "T").
"""
from decimal import Decimal

from oscar.apps.partner import prices, strategy


class PrecioConvenio(strategy.UseFirstStockRecord, strategy.StockRequired, strategy.NoTax, strategy.Structured):
    def __init__(self, request=None, lista=None):
        super().__init__(request)
        self.lista = lista

    def pricing_policy(self, product, stockrecord):
        if self.lista is not None and stockrecord is not None:
            precio = self._precio_lista(product)
            if precio is not None:
                return prices.FixedPrice(
                    currency=stockrecord.price_currency, excl_tax=precio, tax=Decimal("0")
                )
        return super().pricing_policy(product, stockrecord)

    def _precio_lista(self, product):
        from cuentas.models import PrecioLista

        fila = PrecioLista.objects.filter(lista=self.lista, producto=product).only("precio_neto").first()
        return fila.precio_neto if fila else None


def lista_de_precios(user):
    """Lista vigente del cliente B2B al que pertenece el usuario, o None."""
    if user is None or not user.is_authenticated:
        return None
    perfil = getattr(user, "perfil", None)
    cliente = getattr(perfil, "cliente", None) if perfil else None
    if cliente is None or cliente.tipo != "B2B":
        return None
    lista = cliente.lista_precio
    return lista if lista is not None and lista.esta_vigente() else None


class Selector:
    def strategy(self, request=None, user=None, **kwargs):
        if user is None and request is not None:
            user = getattr(request, "user", None)
        return PrecioConvenio(request, lista_de_precios(user))
