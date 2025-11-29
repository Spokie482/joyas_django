from django.contrib import admin
from .models import Producto, Orden, DetalleOrden, Perfil, Favorito, Cupon

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'precio_oferta', 'en_oferta', 'stock')
    search_fields = ('nombre',)
    list_editable = ('en_oferta', 'precio_oferta')
    list_filter = ('categoria', 'en_oferta')

class DetalleOrdenInline(admin.TabularInline):
    model = DetalleOrden
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'precio_unitario')
    can_delete = False

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'total', 'estado')
    list_filter = ('fecha', 'estado')
    list_editable = ('estado',)
    inlines = [DetalleOrdenInline]

# --- NUEVOS REGISTROS ---
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefono', 'ciudad')
    search_fields = ('usuario__username', 'telefono')

@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'producto', 'fecha')
    list_filter = ('fecha',)

@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descuento', 'activo', 'valido_hasta')
    list_filter = ('activo', 'valido_hasta')
    search_fields = ('codigo',)