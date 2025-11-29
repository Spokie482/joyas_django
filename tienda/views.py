from django.shortcuts import render, get_object_or_404 
from .models import Producto
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, get_object_or_404, redirect
from .carrito import Carrito
from django.contrib.auth.decorators import login_required
from .models import Orden, DetalleOrden
from .forms import CheckoutForm
from .forms import CheckoutForm, UserUpdateForm, PerfilUpdateForm
from .models import Perfil
from django.http import JsonResponse
from .models import Favorito
from django.contrib import messages

def catalogo(request):
    # 1. Obtenemos todas las joyas de la base de datos
    joyas = Producto.objects.all()
    query = request.GET.get('q') # 'q' es el nombre que le pusimos al input en el HTML
    # 2. Productos en OFERTA (Solo traemos los que tienen el check activado)
    ofertas = Producto.objects.filter(en_oferta=True)[:5] # Limitamos a 5

    if query:
        # 3. Filtramos: Si el nombre O la descripción contienen el texto
        joyas = joyas.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )
    categoria_filter = request.GET.get('categoria')
    if categoria_filter:
        joyas = joyas.filter(categoria=categoria_filter)

    return render(request, 'tienda/index.html', {
        'joyas': joyas,
        'ofertas': ofertas,
        'categoria_actual': categoria_filter 
    })


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

def agregar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    # 1. Obtener cantidad actual en el carrito (si existe)
    cantidad_en_carrito = 0
    if str(producto.id) in carrito.carrito:
        cantidad_en_carrito = carrito.carrito[str(producto.id)]['cantidad']
        
    # 2. Verificar si podemos agregar uno más
    if cantidad_en_carrito + 1 > producto.stock:
        messages.error(request, f"Lo sentimos, solo quedan {producto.stock} unidades de {producto.nombre}.")
    else:
        carrito.agregar(producto)
        messages.success(request, f"Agregaste {producto.nombre} al carrito.")
        
    return redirect("ver_carrito")

def eliminar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.eliminar(producto)
    return redirect("ver_carrito")

def restar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.restar(producto)
    return redirect("ver_carrito")

def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.vaciar()
    return redirect("ver_carrito")

def ver_carrito(request):
    # 1. Obtenemos el carrito y el total actual
    carrito = Carrito(request)
    total = carrito.obtener_total()
    
    LIMITE_ENVIO_GRATIS = 15000
    
    # 2. Matemáticas: Calculamos cuánto falta
    falta_para_envio = LIMITE_ENVIO_GRATIS - total
    
    # 3. Matemáticas: Calculamos el porcentaje para la barra (0% a 100%)
    if total > 0:
        porcentaje_barra = (total / LIMITE_ENVIO_GRATIS) * 100
    else:
        porcentaje_barra = 0
    
    # Nos aseguramos de que la barra no se pase del 100%
    if porcentaje_barra > 100:
        porcentaje_barra = 100

    # 4. Enviamos TODO al HTML (total, limite, falta y porcentaje)
    return render(request, 'tienda/carrito.html', {
        'total': total,
        'limite_envio': LIMITE_ENVIO_GRATIS,
        'falta_envio': round(falta_para_envio, 2), # Redondeamos a 2 decimales
        'porcentaje_envio': int(porcentaje_barra)
    })


@login_required # <--- Esto obliga a iniciar sesión antes de comprar
def finalizar_compra(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('catalogo')

    # LÓGICA DEL FORMULARIO
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # 1. Crear la orden con los datos del formulario, pero SIN guardarla aún
            orden = form.save(commit=False)
            orden.usuario = request.user
            orden.total = carrito.obtener_total()
            orden.save()
            lista_productos = []
            error_stock = False

            # 2. Guardar los detalles (esto es igual que antes)
            for key, item in carrito.carrito.items():
                producto = get_object_or_404(Producto, id=item["producto_id"])

                if producto.stock < item["cantidad"]:
                    messages.error(request, f"¡Lo sentimos! El producto {producto.nombre} se acaba de agotar o no hay suficiente stock.")
                    error_stock = True
                    break

                DetalleOrden.objects.create(
                    orden=orden,
                    producto=producto,
                    cantidad=item["cantidad"],
                    precio_unitario=float(item["precio"])
                )
                # Restar stock
                producto.stock -= item["cantidad"]
                producto.save()

                lista_productos.append(f"- {item['cantidad']}x {producto.nombre}")

            if error_stock:
                # Si hubo error, borramos la orden incompleta y volvemos al carrito
                orden.delete()
                return redirect('ver_carrito')

            # 3. Limpiar y redigir
            carrito.vaciar()
            return render(request, 'tienda/compra_exitosa.html', {'orden': orden})
    else:
        # Si entramos por GET, mostramos el formulario vacío
        form = CheckoutForm()

    return render(request, 'tienda/checkout.html', {'form': form, 'carrito': carrito})


def mis_compras(request):
    # Buscamos solo las órdenes de ESTE usuario, ordenadas de la más nueva a la más vieja
    ordenes = Orden.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'tienda/mis_compras.html', {'ordenes': ordenes})

def editar_perfil(request):
    # --- BLOQUE DE SEGURIDAD (NUEVO) ---
    try:
        # Intentamos acceder al perfil
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        # Si no existe (porque es un usuario viejo), lo creamos manual
        perfil = Perfil.objects.create(usuario=request.user)
    
    
    if request.method == 'POST':
        # Cargamos los datos enviados en ambos formularios
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = PerfilUpdateForm(request.POST, request.FILES, instance=perfil)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            # Redirigimos a la misma página o a 'mis compras' para mostrar éxito
            return redirect('editar_perfil') 
    else:
        # Si es GET, mostramos los formularios con los datos actuales
        u_form = UserUpdateForm(instance=request.user)
        p_form = PerfilUpdateForm(instance=perfil)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'tienda/editar_perfil.html', context)

@login_required
def toggle_favorito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Buscamos si ya existe el like
    favorito_existente = Favorito.objects.filter(usuario=request.user, producto=producto).first()
    
    if favorito_existente:
        # Si existe, lo borramos (Dislike)
        favorito_existente.delete()
        agregado = False
    else:
        # Si no existe, lo creamos (Like)
        Favorito.objects.create(usuario=request.user, producto=producto)
        agregado = True
    
    # Devolvemos una respuesta JSON para que Javascript la lea sin recargar
    return JsonResponse({'agregado': agregado})

@login_required
def mis_favoritos(request):
    # Obtenemos los favoritos ordenados por fecha (más recientes primero)
    favoritos = Favorito.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'tienda/mis_favoritos.html', {'favoritos': favoritos})