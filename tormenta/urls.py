from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from tienda import views
from django.contrib.sitemaps.views import sitemap
from tienda.sitemaps import ProductoSitemap, StaticViewSitemap
from django.views.generic.base import TemplateView

#diccionario de mapas
sitemaps = {
    'productos': ProductoSitemap,
    'estaticas': StaticViewSitemap,
}




# Definimos las rutas UNA sola vez
urlpatterns = [
    path('admin/', admin.site.urls),  # <--- Acceso al panel
    
    path('accounts/login/', auth_views.LoginView.as_view(template_name='tienda/login.html'), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),

    path('registro/', views.registro, name='registro'),
    path('', views.catalogo, name='catalogo'), # <--- Página principal
    path('producto/<int:producto_id>/', views.detalle, name='detalle'), # <--- Página de detalle
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),

    path('mis-compras/', views.mis_compras, name='mis_compras'),

    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_carrito, name='agregar_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_carrito, name='eliminar_carrito'),
    path('carrito/restar/<int:producto_id>/', views.restar_carrito, name='restar_carrito'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    path('carrito/finalizar/', views.finalizar_compra, name='finalizar_compra'),

    path('favoritos/toggle/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('mis-favoritos/', views.mis_favoritos, name='mis_favoritos'),

    path('carrito/cupon/', views.aplicar_cupon, name='aplicar_cupon'),

    path('dashboard/', views.dashboard_admin, name='dashboard_admin'),

    path('busqueda-ajax/', views.buscar_productos_ajax, name='buscar_productos_ajax'),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

]


# Configuración para ver las imágenes (siempre al final)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)