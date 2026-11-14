"""Listado del catálogo leído directamente desde PostgreSQL.

Oscar 4 arma el catálogo con un motor de búsqueda (Haystack). Con el motor "simple"
—el único que no requiere un servidor Solr adicional— el listado sin término de
búsqueda sale vacío. Estas vistas reemplazan solo el listado y reutilizan las
plantillas de Oscar; la búsqueda por texto (/search/) sigue usando Haystack.
"""
from types import SimpleNamespace

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView
from oscar.core.loading import get_model

Product = get_model("catalogue", "Product")
Category = get_model("catalogue", "Category")


class _ListadoProductos(ListView):
    context_object_name = "products"
    paginate_by = settings.OSCAR_PRODUCTS_PER_PAGE

    def base(self):
        return (
            Product.objects.browsable()
            .filter(is_public=True)
            .select_related("product_class")
            .prefetch_related("stockrecords", "images")
            .order_by("-priority", "title")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Las plantillas de Oscar esperan resultados de búsqueda con el producto en ".object"
        ctx["products"] = [SimpleNamespace(object=p) for p in ctx["products"]]
        return ctx


class CatalogoView(_ListadoProductos):
    template_name = "oscar/catalogue/browse.html"

    def get_queryset(self):
        return self.base()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["summary"] = "Todos los productos"
        return ctx


class CategoriaView(_ListadoProductos):
    template_name = "oscar/catalogue/category.html"

    def dispatch(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, pk=kwargs["pk"])
        if not (self.category.is_public or request.user.is_staff):
            from django.http import Http404

            raise Http404
        if self.category.get_absolute_url() != request.path:
            return redirect(self.category.get_absolute_url(), permanent=True)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.base().filter(categories__in=self.category.get_descendants_and_self()).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["category"] = self.category
        ctx["summary"] = self.category.name
        return ctx
