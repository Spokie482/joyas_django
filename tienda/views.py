from django.shortcuts import render, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, get_object_or_404, redirect
from .carrito import Carrito
from django.contrib.auth.decorators import login_required
from .models import Orden, DetalleOrden, Cupon, Favorito, Perfil, Review, Producto
from .forms import CheckoutForm, UserUpdateForm, PerfilUpdateForm, ReviewForm
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
import json
from django.contrib.auth.models import User

def catalogo(request):
    # 1. Base: Traemos TODOS los productos disponibles
    productos = Producto.objects.all()
    
    # --- FILTROS GLOBALES (Funcionan para Joyas, Ropa y Maquillaje) ---
    
    # A. Búsqueda por Texto
    query = request.GET.get('q')
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )

    # B. Filtro por Categoría
    categoria_filter = request.GET.get('categoria')
    if categoria_filter:
        productos = productos.filter(categoria=categoria_filter)

    # C. Filtro por Rango de Precio (Nuevo)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price:
        productos = productos.filter(precio__gte=min_price)
    if max_price:
        productos = productos.filter(precio__lte=max_price)

    # D. Ordenamiento (Nuevo)
    # opciones: 'reciente', 'precio_asc', 'precio_desc'
    orden = request.GET.get('orden', 'reciente') # Por defecto: reciente
    
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    else:
        # Por defecto: lo último que agregaste (ideal para novedades de ropa/makeup)
        productos = productos.order_by('-id') 


    # Solo para el slider de ofertas (sigue igual)
    ofertas = Producto.objects.filter(en_oferta=True)[:5]

    return render(request, 'tienda/index.html', {
        'joyas': productos, # Usamos la misma variable para no romper el HTML
        'ofertas': ofertas,
        'categoria_actual': categoria_filter,
    })

def detalle(request, producto_id):
    joya = get_object_or_404(Producto, pk=producto_id)
    
    # --- 1. LÓGICA DE RESEÑAS ---
    # Procesar el formulario si se envió (método POST)
    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.producto = joya
            review.usuario = request.user
            review.save()
            messages.success(request, "¡Gracias por tu opinión!")
            # Redirigimos a la misma página para ver el comentario nuevo
            return redirect('detalle', producto_id=joya.id)
    else:
        # Si es GET (solo ver la página), el formulario está vacío
        form = ReviewForm()

    # Obtener todas las reseñas de este producto
    reviews = joya.reviews.all().order_by('-fecha')
    
    # Calcular el promedio de estrellas
    promedio_stars = 0
    if reviews.exists():
        promedio_stars = reviews.aggregate(Avg('calificacion'))['calificacion__avg']

    # --- 2. LÓGICA DE RECOMENDACIONES (La que ya tenías) ---
    min_price = joya.precio * Decimal('0.5')
    max_price = joya.precio * Decimal('2.0')

    relacionados = Producto.objects.filter(
        categoria=joya.categoria,
        stock__gt=0,
        precio__gte=min_price,
        precio__lte=max_price
    ).exclude(id=joya.id).order_by('?')[:4]

    if relacionados.count() < 4:
        productos_extra = Producto.objects.filter(
            categoria=joya.categoria,
            stock__gt=0
        ).exclude(id=joya.id).exclude(id__in=[p.id for p in relacionados]).order_by('?')[:4 - relacionados.count()]
        
        relacionados = list(relacionados) + list(productos_extra)

    return render(request, 'tienda/detalle.html', {
        'joya': joya,
        'relacionados': relacionados,
        'reviews': reviews,           # <--- Nuevo: Lista de comentarios
        'form': form,                 # <--- Nuevo: El formulario
        'promedio_stars': round(promedio_stars or 0, 1) # <--- Nuevo: Promedio redondeado
    })

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

    descuento_monto = 0
    cupon_id = request.session.get('cupon_id')
    nombre_cupon = None
    
    if cupon_id:
        try:
            cupon = Cupon.objects.get(id=cupon_id)
            # Calculamos el descuento (Ej: 1000 * 20 / 100 = 200 de descuento)
            descuento_monto = (total * cupon.descuento) / 100
            nombre_cupon = cupon.codigo
        except Cupon.DoesNotExist:
            del request.session['cupon_id'] # Limpiamos si el cupón se borró de la BD

    total_final = total - descuento_monto
    
    LIMITE_ENVIO_GRATIS = 30000
    
    
    falta_para_envio = LIMITE_ENVIO_GRATIS - total_final
    
    
    if total_final > 0:
        porcentaje_barra = (total_final / LIMITE_ENVIO_GRATIS) * 100
    else:
        porcentaje_barra = 0
    
    if porcentaje_barra > 100:
        porcentaje_barra = 100

    
    return render(request, 'tienda/carrito.html', {
        'total': total,
        'total_final': total_final,
        'limite_envio': LIMITE_ENVIO_GRATIS,
        'falta_envio': round(falta_para_envio, 2), 
        'porcentaje_envio': int(porcentaje_barra)
    })


@login_required
def finalizar_compra(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('catalogo')

    # --- LÓGICA MATEMÁTICA CENTRALIZADA ---
    # 1. Subtotal
    subtotal = carrito.obtener_total()
    
    # 2. Descuento
    descuento_monto = 0
    cupon_id = request.session.get('cupon_id')
    
    if cupon_id:
        try:
            cupon = Cupon.objects.get(id=cupon_id)
            descuento_monto = (subtotal * cupon.descuento) / 100
        except Cupon.DoesNotExist:
            del request.session['cupon_id']

    total_con_descuento = subtotal - descuento_monto

    # 3. Envío
    LIMITE_ENVIO_GRATIS = 30000
    COSTO_ENVIO_FIJO = 5000 # 👈 Define aquí cuánto cuesta el envío normal
    
    costo_envio = 0
    if total_con_descuento < LIMITE_ENVIO_GRATIS:
        costo_envio = COSTO_ENVIO_FIJO
    
    # 4. TOTAL FINAL REAL
    total_a_pagar = total_con_descuento + costo_envio
    # ---------------------------------------

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            orden = form.save(commit=False)
            orden.usuario = request.user
            # Guardamos el total CORRECTO (con envío y descuento)
            orden.total = total_a_pagar 
            orden.save()

            # Guardar detalles
            lista_productos = []
            for key, item in carrito.carrito.items():
                producto = get_object_or_404(Producto, id=item["producto_id"])
                DetalleOrden.objects.create(
                    orden=orden,
                    producto=producto,
                    cantidad=item["cantidad"],
                    precio_unitario=float(item["precio"])
                )
                producto.stock -= item["cantidad"]
                producto.save()
                lista_productos.append(f"- {item['cantidad']}x {producto.nombre}")

            # Enviar correo (código anterior)...
            # (Pega aquí tu bloque de envío de correo si ya lo tenías configurado)

            carrito.vaciar()
            # Limpiamos el cupón de la sesión al terminar
            if 'cupon_id' in request.session:
                del request.session['cupon_id']
                
            return render(request, 'tienda/compra_exitosa.html', {'orden': orden})
    else:
        form = CheckoutForm()

    return render(request, 'tienda/checkout.html', {
        'form': form, 
        'carrito': carrito,
        # Enviamos los valores calculados al HTML
        'subtotal': subtotal,
        'descuento': descuento_monto,
        'costo_envio': costo_envio,
        'total_a_pagar': total_a_pagar
    })

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

def aplicar_cupon(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo_cupon')
        try:
            # Buscamos un cupón que coincida, esté activo y en fecha válida
            cupon = Cupon.objects.get(
                codigo__iexact=codigo,
                activo=True,
                valido_desde__lte=timezone.now(),
                valido_hasta__gte=timezone.now()
            )
            # Guardamos el ID del cupón en la "memoria" del navegador (sesión)
            request.session['cupon_id'] = cupon.id
            messages.success(request, f"¡Cupón {cupon.codigo} aplicado con éxito!")
        except Cupon.DoesNotExist:
            request.session['cupon_id'] = None
            messages.error(request, "Este cupón no es válido o ha expirado.")
            
    return redirect('ver_carrito')

@staff_member_required
def dashboard_admin(request):
    # ... (Mantén tus KPIs anteriores: total_usuarios, total_ordenes, etc.) ...
    total_usuarios = User.objects.count()
    total_ordenes = Orden.objects.count()
    ingresos_totales = Orden.objects.aggregate(Sum('total'))['total__sum'] or 0
    low_stock_count = Producto.objects.filter(stock__lte=3).count()

    # --- NUEVA DATA PARA EL DASHBOARD (RESEÑAS) ---
    # 1. Promedio General de Calidad (De 1 a 5 estrellas)
    promedio_calidad = Review.objects.aggregate(Avg('calificacion'))['calificacion__avg'] or 0

    # 2. Últimas 3 Reseñas para monitorear
    ultimas_reviews = Review.objects.order_by('-fecha')[:3]
    # ---------------------------------------------

    # ... (Mantén la lógica de tus gráficos y órdenes recientes) ...
    ordenes_por_estado = Orden.objects.values('estado').annotate(cantidad=Count('id'))
    labels_estados = [x['estado'] for x in ordenes_por_estado]
    data_estados = [x['cantidad'] for x in ordenes_por_estado]

    top_productos = DetalleOrden.objects.values('producto__nombre').annotate(
        total_vendido=Sum('cantidad')
    ).order_by('-total_vendido')[:5]
    labels_top = [x['producto__nombre'] for x in top_productos]
    data_top = [x['total_vendido'] for x in top_productos]

    ordenes_recientes = Orden.objects.order_by('-fecha')[:5]

    return render(request, 'tienda/dashboard.html', {
        'total_usuarios': total_usuarios,
        'total_ordenes': total_ordenes,
        'ingresos_totales': ingresos_totales,
        'low_stock_count': low_stock_count,
        'ordenes_recientes': ordenes_recientes,

        # Pasamos los nuevos datos
        'promedio_calidad': round(promedio_calidad, 1),
        'ultimas_reviews': ultimas_reviews,

        'labels_estados': json.dumps(labels_estados),
        'data_estados': json.dumps(data_estados),
        'labels_top': json.dumps(labels_top),
        'data_top': json.dumps(data_top),
    })