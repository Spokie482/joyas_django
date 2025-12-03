from .carrito import Carrito

def carrito_context(request):
    """
    Context processor para disponibilizar datos del carrito en todos los templates.
    """
    carrito = Carrito(request)
    cantidad_total = sum(int(item['cantidad']) for item in carrito.carrito.values())
    
    return {
        'carrito_total_monto': carrito.obtener_total(),
        'carrito_cantidad_items': cantidad_total
    }
