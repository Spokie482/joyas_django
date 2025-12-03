from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.catalogo, name='catalogo'),
    path('registro/', views.registro, name='registro'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='tienda/login.html'), name='login'),
    
    path('producto/<int:producto_id>/', views.detalle, name='detalle'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('mis-compras/', views.mis_compras, name='mis_compras'),

    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_carrito, name='agregar_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_carrito, name='eliminar_carrito'),
    path('carrito/restar/<int:producto_id>/', views.restar_carrito, name='restar_carrito'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    path('carrito/finalizar/', views.finalizar_compra, name='finalizar_compra'),
    path('carrito/cupon/', views.aplicar_cupon, name='aplicar_cupon'),

    path('favoritos/toggle/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('mis-favoritos/', views.mis_favoritos, name='mis_favoritos'),

    path('dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('busqueda-ajax/', views.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('review/eliminar/<int:review_id>/', views.eliminar_review, name='eliminar_review'),
]
