

# Register your models here.
from django.contrib import admin
from .models import Producto, Orden, DetalleOrden

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'precio_oferta', 'en_oferta', 'stock')
    search_fields = ('nombre',)
    list_editable = ('en_oferta', 'precio_oferta')
    list_filter = ('categoria', 'en_oferta')
    

# --- 2. Configuración de ÓRDENES (Lo nuevo) ---

# Esto crea la tabla pequeña dentro de la Orden para ver qué compraron
class DetalleOrdenInline(admin.TabularInline):
    model = DetalleOrden
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'precio_unitario')
    can_delete = False

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'total')
    list_filter = ('fecha',)
    # Aquí conectamos la tabla de productos con la orden
    inlines = [DetalleOrdenInline]