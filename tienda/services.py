from django.db import transaction
from .models import Orden, DetalleOrden, Producto, Variante, Cupon

def procesar_compra(usuario, carrito, datos_orden, cupon_id=None):
    """
    Procesa la compra: crea la orden, valida stock, crea detalles y actualiza stock.
    Retorna la orden creada.
    Lanza ValueError si hay problemas de stock o validación.
    """
    total_a_pagar = datos_orden['total']
    
    with transaction.atomic():
        # 1. Crear la Orden
        orden = Orden.objects.create(
            usuario=usuario,
            total=total_a_pagar,
            direccion=datos_orden.get('direccion', ''),
            ciudad=datos_orden.get('ciudad', ''),
            codigo_postal=datos_orden.get('codigo_postal', ''),
            telefono=datos_orden.get('telefono', '')
        )

        # 2. Procesar Items del Carrito
        for key, item in carrito.items():
            # Bloqueamos el producto para evitar condiciones de carrera
            producto = Producto.objects.select_for_update().get(id=item["producto_id"])
            variante_id = item.get("variante_id")
            variante_obj = None
            cantidad = int(item["cantidad"])

            if variante_id:
                # Bloqueamos la variante también
                variante_obj = Variante.objects.select_for_update().get(id=variante_id)
                stock_actual = variante_obj.stock
                nombre_ref = f"{producto.nombre} ({variante_obj.nombre})"
            else:
                stock_actual = producto.stock
                nombre_ref = producto.nombre

            # 3. Validar Stock
            if stock_actual < cantidad:
                raise ValueError(f"Lo sentimos, ya no hay suficiente stock de {nombre_ref}.")

            precio_final_unitario = producto.precio_actual

            # 4. Crear Detalle de Orden
            DetalleOrden.objects.create(
                orden=orden,
                producto=producto,
                variante=variante_obj,
                cantidad=cantidad,
                precio_unitario=precio_final_unitario
            )

            # 5. Actualizar Stock
            if variante_obj:
                variante_obj.stock -= cantidad
                variante_obj.save()
            else:
                producto.stock -= cantidad
                producto.save()

        # 6. Registrar uso del cupón (si existe)
        if cupon_id:
            try:
                cupon_usado = Cupon.objects.select_for_update().get(id=cupon_id)
                cupon_usado.usuarios_usados.add(usuario) 
            except Cupon.DoesNotExist:
                pass
                
    return orden
