from django.shortcuts import render, get_object_or_404 
from .models import Producto
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, get_object_or_404, redirect

def catalogo(request):
    # 1. Obtenemos todas las joyas de la base de datos
    joyas = Producto.objects.all()
    query = request.GET.get('q') # 'q' es el nombre que le pusimos al input en el HTML

    if query:
        # 3. Filtramos: Si el nombre O la descripción contienen el texto
        joyas = joyas.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )
    # 2. Se las enviamos al HTML (index.html)
    return render(request, 'tienda/index.html', {'joyas': joyas})


# 👇 ESTA ES LA NUEVA FUNCIÓN
def detalle(request, producto_id):
    # Busca el producto por su ID o da error 404 si no existe
    joya = get_object_or_404(Producto, pk=producto_id)
    return render(request, 'tienda/detalle.html', {'joya': joya})

def registro(request):
    if request.method == 'POST':
        # Si llenaron el formulario y le dieron a "Enviar"
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Iniciar sesión automáticamente después de registrarse
            login(request, user)
            return redirect('catalogo')
    else:
        # Si apenas entraron a la página (formulario vacío)
        form = UserCreationForm()
    
    return render(request, 'tienda/registro.html', {'form': form})