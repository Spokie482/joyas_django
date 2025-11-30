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
    list_display = ('codigo', 'descuento', 'activo', 'valido_hasta', 'usuarios_que_lo_usaron')
    list_filter = ('activo', 'valido_hasta')
    search_fields = ('codigo',)
    
    filter_horizontal = ('usuarios_usados',) 

    # Muestra un contador en la lista principal
    def usuarios_que_lo_usaron(self, obj):
        return obj.usuarios_usados.count()
    usuarios_que_lo_usaron.short_description = "Veces Usado"

    # 2. ACCIÓN RÁPIDA (Botón Reset)
    actions = ['resetear_historial']

    @admin.action(description="🔄 Resetear usuarios (Permitir usar de nuevo)")
    def resetear_historial(self, request, queryset):
        for cupon in queryset:
            cupon.usuarios_usados.clear() # Borra todas las relaciones
        self.message_user(request, "¡Historial de usuarios borrado! Ahora pueden volver a usar estos cupones.")