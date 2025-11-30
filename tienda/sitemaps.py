from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Producto

class ProductoSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        # Solo incluimos en el mapa los productos con stock
        return Producto.objects.filter(stock__gt=0)

    def location(self, obj):
        return f'/producto/{obj.id}/'

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['catalogo', 'login', 'registro']

    def location(self, item):
        return reverse(item)