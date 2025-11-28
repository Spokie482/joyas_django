from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from tienda import views

# Definimos las rutas UNA sola vez
urlpatterns = [
    path('admin/', admin.site.urls),  # <--- Acceso al panel
    
    path('accounts/login/', auth_views.LoginView.as_view(template_name='tienda/login.html'), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),

    path('registro/', views.registro, name='registro'),
    path('', views.catalogo, name='catalogo'), # <--- Página principal
    path('producto/<int:producto_id>/', views.detalle, name='detalle'), # <--- Página de detalle
]

# Configuración para ver las imágenes (siempre al final)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)