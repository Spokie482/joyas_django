from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .carrito import Carrito
from django.contrib.auth.decorators import login_required
from .models import Orden, DetalleOrden, Cupon, Favorito, Perfil, Review, Producto, Categoria, Variante
from .forms import CheckoutForm, UserUpdateForm, PerfilUpdateForm, ReviewForm
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
import json
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.db import transaction
from django.core.cache import cache

def catalogo(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    
    query = request.GET.get('q')
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )

    categoria_filter = request.GET.get('categoria')
    if categoria_filter:
        productos = productos.filter(categoria__slug=categoria_filter)

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price:
        productos = productos.filter(precio__gte=min_price)
    if max_price:
        productos = productos.filter(precio__lte=max_price)

    categoria_slug = request.GET.get('categoria')
    if categoria_slug:
        productos = productos.filter(categoria__slug=categoria_slug)

    orden = request.GET.get('orden', 'reciente')
    
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('-id') 

    ofertas = Producto.objects.filter(en_oferta=True)[:5]

    return render(request, 'tienda/index.html', {
        'joyas': productos,
        'ofertas': ofertas,
        'categorias': categorias,
        'categoria_actual': categoria_slug,
    })

def detalle(request, producto_id):
    joya = get_object_or_404(Producto, pk=producto_id)
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.producto = joya
            review.usuario = request.user
            review.save()
            messages.success(request, "¡Gracias por tu opinión!")
            return redirect('detalle', producto_id=joya.id)
    else:
        form = ReviewForm()

    reviews = joya.reviews.all().order_by('-fecha')
    
    promedio_stars = 0
    if reviews.exists():
        promedio_stars = reviews.aggregate(Avg('calificacion'))['calificacion__avg']

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
        'reviews': reviews,
        'form': form,
        'promedio_stars': round(promedio_stars or 0, 1)
    })

@login_required
def eliminar_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    
    if request.user == review.usuario or request.user.is_staff:
        review.delete()
        messages.success(request, "Comentario eliminado correctamente.")
    else:
        messages.error(request, "No tienes permiso para eliminar este comentario.")
    
    return redirect('detalle', producto_id=review.producto.id)

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect('catalogo')
    else:
        form = UserCreationForm()
    return render(request, 'tienda/registro.html', {'form': form})

def agregar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)

    variante_id = request.POST.get('variante') or request.GET.get('variante')
    variante_obj = None
    
    if variante_id:
        variante_obj = get_object_or_404(Variante, id=variante_id)

    if variante_obj:
        cart_id = f"{producto.id}_{variante_obj.id}"
        stock_disponible = variante_obj.stock
        nombre_producto = f"{producto.nombre} ({variante_obj.nombre})"
    else:
        cart_id = str(producto.id)
        stock_disponible = producto.stock
        nombre_producto = producto.nombre

    cantidad_en_carrito = 0
    if cart_id in carrito.carrito:
        cantidad_en_carrito = carrito.carrito[cart_id]['cantidad']
        
    if cantidad_en_carrito + 1 > stock_disponible:
        messages.error(request, f"Lo sentimos, solo quedan {stock_disponible} unidades de {nombre_producto}.")
    else:
        carrito.agregar(producto, variante=variante_obj)
        messages.success(request, f"Agregaste {nombre_producto} al carrito.")
       
    return redirect("ver_carrito")

def restar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    variante_id = request.GET.get('variante')
    variante_obj = get_object_or_404(Variante, id=variante_id) if variante_id else None
    
    carrito.restar(producto, variante=variante_obj)
    return redirect("ver_carrito")

def eliminar_carrito(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    variante_id = request.GET.get('variante')
    variante_obj = get_object_or_404(Variante, id=variante_id) if variante_id else None
    
    carrito.eliminar(producto, variante=variante_obj)
    return redirect("ver_carrito")

def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.vaciar()
    return redirect("ver_carrito")

def ver_carrito(request):
    carrito = Carrito(request)
    total = carrito.obtener_total()

    descuento_monto = 0
    cupon_id = request.session.get('cupon_id')
    nombre_cupon = None
    
    if cupon_id:
        try:
            cupon = Cupon.objects.get(id=cupon_id)
            descuento_monto = (total * cupon.descuento) / 100
            nombre_cupon = cupon.codigo
        except Cupon.DoesNotExist:
            del request.session['cupon_id']

    total_final = total - descuento_monto
    
    LIMITE_ENVIO_GRATIS = 30000
    falta_para_envio = max(0, LIMITE_ENVIO_GRATIS - total_final)
     
    if total_final > 0:
        porcentaje_barra = (total_final / LIMITE_ENVIO_GRATIS) * 100
    else:
        porcentaje_barra = 0
    
    if porcentaje_barra > 100:
        porcentaje_barra = 100

    segundos_restantes = 0
    ultimo_acceso = request.session.get("carrito_ultimo_acceso")
    
    if carrito.carrito and ultimo_acceso:
        try:
            ahora = datetime.now()
            tiempo_ultimo = datetime.fromisoformat(ultimo_acceso)
            expiracion = tiempo_ultimo + timedelta(hours=2)
            diferencia = expiracion - ahora
            segundos_restantes = max(0, diferencia.total_seconds())
        except ValueError:
            pass

    items_visuales = []
    bloquear_checkout = False

    for key, item in carrito.carrito.items():
        try:
            producto = Producto.objects.get(id=item["producto_id"])
            stock_actual = 0
            
            if item["variante_id"]:
                variante = Variante.objects.get(id=item["variante_id"])
                stock_actual = variante.stock
            else:
                stock_actual = producto.stock
            
            cantidad_en_carrito = int(item["cantidad"])
            
            tiene_stock = stock_actual >= cantidad_en_carrito
            llegamos_al_limite = cantidad_en_carrito >= stock_actual
            
            if not tiene_stock:
                bloquear_checkout = True
            
            item_display = item.copy()
            item_display['tiene_stock'] = tiene_stock
            item_display['llegamos_al_limite'] = llegamos_al_limite
            item_display['stock_real'] = stock_actual
            
            items_visuales.append(item_display)

        except (Producto.DoesNotExist, Variante.DoesNotExist):
            continue

    return render(request, 'tienda/carrito.html', {
        'total': total,
        'total_final': total_final,
        'limite_envio': LIMITE_ENVIO_GRATIS,
        'falta_envio': round(falta_para_envio, 2), 
        'porcentaje_envio': int(porcentaje_barra),
        'segundos_restantes': int(segundos_restantes),
        'items_visuales': items_visuales,
        'bloquear_checkout': bloquear_checkout,
        'nombre_cupon': nombre_cupon,
        'descuento': descuento_monto
    })

@login_required
def finalizar_compra(request):
    carrito = Carrito(request)
    if not carrito.carrito:
        return redirect('catalogo')

    subtotal = carrito.obtener_total()
    
    descuento_monto = 0
    cupon_id = request.session.get('cupon_id')
    
    if cupon_id:
        try:
            cupon = Cupon.objects.get(id=cupon_id)
            descuento_monto = (subtotal * cupon.descuento) / 100
        except Cupon.DoesNotExist:
            del request.session['cupon_id']

    total_con_descuento = subtotal - descuento_monto

    LIMITE_ENVIO_GRATIS = 30000
    COSTO_ENVIO_FIJO = 5000
    
    costo_envio = 0
    if total_con_descuento < LIMITE_ENVIO_GRATIS:
        costo_envio = COSTO_ENVIO_FIJO
    
    total_a_pagar = total_con_descuento + costo_envio

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    orden = form.save(commit=False)
                    orden.usuario = request.user
                    orden.total = total_a_pagar
                    orden.save()

                    for key, item in carrito.carrito.items():
                        producto = Producto.objects.select_for_update().get(id=item["producto_id"])
                        variante_id = item.get("variante_id")
                        variante_obj = None
                        cantidad = int(item["cantidad"])

                        if variante_id:
                            variante_obj = Variante.objects.select_for_update().get(id=variante_id)
                            stock_actual = variante_obj.stock
                            nombre_ref = f"{producto.nombre} ({variante_obj.nombre})"
                        else:
                            stock_actual = producto.stock
                            nombre_ref = producto.nombre

                        if stock_actual < cantidad:
                            raise ValueError(f"Lo sentimos, ya no hay suficiente stock de {nombre_ref}.")

                        if producto.en_oferta and producto.precio_oferta:
                            precio_final_unitario = producto.precio_oferta
                        else:
                            precio_final_unitario = producto.precio

                        DetalleOrden.objects.create(
                            orden=orden,
                            producto=producto,
                            variante=variante_obj,
                            cantidad=cantidad,
                            precio_unitario=precio_final_unitario
                        )

                        if variante_obj:
                            variante_obj.stock -= cantidad
                            variante_obj.save()
                        else:
                            producto.stock -= cantidad
                            producto.save()

                    if 'cupon_id' in request.session:
                        try:
                            cupon_usado = Cupon.objects.select_for_update().get(id=request.session['cupon_id'])
                            cupon_usado.usuarios_usados.add(request.user) 
                        except Cupon.DoesNotExist:
                            pass

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('ver_carrito')
            
            except Exception as e:
                messages.error(request, "Error inesperado al procesar la compra.")
                return redirect('ver_carrito')

            carrito.vaciar()
            
            if 'cupon_id' in request.session:
                del request.session['cupon_id']
                
            return render(request, 'tienda/compra_exitosa.html', {'orden': orden})
    else:
        form = CheckoutForm()

    return render(request, 'tienda/checkout.html', {
        'form': form, 
        'carrito': carrito,
        'subtotal': subtotal,
        'descuento': descuento_monto,
        'costo_envio': costo_envio,
        'total_a_pagar': total_a_pagar
    })

def mis_compras(request):
    ordenes = Orden.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'tienda/mis_compras.html', {'ordenes': ordenes})

def editar_perfil(request):
    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil.objects.create(usuario=request.user)
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = PerfilUpdateForm(request.POST, request.FILES, instance=perfil)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('editar_perfil') 
    else:
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
    
    favorito_existente = Favorito.objects.filter(usuario=request.user, producto=producto).first()
    
    if favorito_existente:
        favorito_existente.delete()
        agregado = False
    else:
        Favorito.objects.create(usuario=request.user, producto=producto)
        agregado = True
    
    return JsonResponse({'agregado': agregado})

@login_required
def mis_favoritos(request):
    favoritos = Favorito.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'tienda/mis_favoritos.html', {'favoritos': favoritos})

def aplicar_cupon(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo_cupon')
        try:
            cupon = Cupon.objects.get(
                codigo__iexact=codigo,
                activo=True,
                valido_desde__lte=timezone.now(),
                valido_hasta__gte=timezone.now()
            )
            
            if request.user.is_authenticated and request.user in cupon.usuarios_usados.all():
                messages.error(request, f"Ya has utilizado el cupón {cupon.codigo} anteriormente.")
                request.session['cupon_id'] = None
            else:
                request.session['cupon_id'] = cupon.id
                messages.success(request, f"¡Cupón {cupon.codigo} aplicado con éxito!")
                
        except Cupon.DoesNotExist:
            request.session['cupon_id'] = None
            messages.error(request, "Este cupón no es válido o ha expirado.")
            
    return redirect('ver_carrito')

@staff_member_required
def dashboard_admin(request):
    # Intentar obtener datos del cache
    cache_key = 'dashboard_stats'
    stats = cache.get(cache_key)

    if not stats:
        total_usuarios = User.objects.count()
        total_ordenes = Orden.objects.count()
        ingresos_totales = Orden.objects.aggregate(Sum('total'))['total__sum'] or 0
        low_stock_count = Producto.objects.filter(stock__lte=3).count()

        promedio_calidad = Review.objects.aggregate(Avg('calificacion'))['calificacion__avg'] or 0

        ordenes_por_estado = Orden.objects.values('estado').annotate(cantidad=Count('id'))
        labels_estados = [x['estado'] for x in ordenes_por_estado]
        data_estados = [x['cantidad'] for x in ordenes_por_estado]

        top_productos = DetalleOrden.objects.values('producto__nombre').annotate(
            total_vendido=Sum('cantidad')
        ).order_by('-total_vendido')[:5]
        labels_top = [x['producto__nombre'] for x in top_productos]
        data_top = [x['total_vendido'] for x in top_productos]
        
        stats = {
            'total_usuarios': total_usuarios,
            'total_ordenes': total_ordenes,
            'ingresos_totales': ingresos_totales,
            'low_stock_count': low_stock_count,
            'promedio_calidad': promedio_calidad,
            'labels_estados': labels_estados,
            'data_estados': data_estados,
            'labels_top': labels_top,
            'data_top': data_top,
        }
        # Cache por 15 minutos
        cache.set(cache_key, stats, 60 * 15)

    # Optimización N+1: Usar select_related para traer relaciones en una sola query
    ultimas_reviews = Review.objects.select_related('usuario', 'producto').order_by('-fecha')[:3]
    ordenes_recientes = Orden.objects.select_related('usuario').order_by('-fecha')[:5]

    return render(request, 'tienda/dashboard.html', {
        'total_usuarios': stats['total_usuarios'],
        'total_ordenes': stats['total_ordenes'],
        'ingresos_totales': stats['ingresos_totales'],
        'low_stock_count': stats['low_stock_count'],
        'ordenes_recientes': ordenes_recientes,
        'promedio_calidad': round(stats['promedio_calidad'], 1),
        'ultimas_reviews': ultimas_reviews,
        'labels_estados': json.dumps(stats['labels_estados']),
        'data_estados': json.dumps(stats['data_estados']),
        'labels_top': json.dumps(stats['labels_top']),
        'data_top': json.dumps(stats['data_top']),
    })

def buscar_productos_ajax(request):
    query = request.GET.get('q', '')
    resultados = []
    
    if len(query) > 2:
        productos = Producto.objects.filter(nombre__icontains=query)[:5]
        for p in productos:
            resultados.append({
                'id': p.id,
                'nombre': p.nombre,
                'precio': str(p.precio),
                'imagen': p.imagen.url if p.imagen else '',
                'url': f"/producto/{p.id}/"
            })
    
    return JsonResponse({'resultados': resultados})