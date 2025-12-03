from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from tienda.models import Producto, Variante

class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        carrito = self.session.get("carrito")
        ultimo_acceso = self.session.get("carrito_ultimo_acceso")

        if ultimo_acceso:
            try:
                ahora = datetime.now()
                tiempo_ultimo = datetime.fromisoformat(ultimo_acceso)
                # Si pasaron más de 2 horas (7200 segundos)
                if ahora - tiempo_ultimo > timedelta(hours=2):
                    carrito = {} # Vaciamos localmente
                    self.session["carrito"] = {} # Vaciamos en sesión
                    if "carrito_ultimo_acceso" in self.session:
                        del self.session["carrito_ultimo_acceso"]
            except ValueError:
                pass # Si hay error de formato, ignoramos

        if not carrito:
            carrito = self.session["carrito"] = {}
            
        self.carrito = carrito

    def agregar(self, producto, variante=None):
        # 1. Definir precio base
        if producto.en_oferta and producto.precio_oferta:
            precio_final = producto.precio_oferta
        else:
            precio_final = producto.precio
        
        # 2. Definir ID única y Nombre
        if variante:
            cart_id = f"{producto.id}_{variante.id}" # ID única para la variante
            nombre_mostrar = f"{producto.nombre} ({variante.nombre})"
            # Si la variante tuviera precio distinto, se cambiaría aquí
        else:
            cart_id = str(producto.id) # ID normal para producto simple
            nombre_mostrar = producto.nombre

        # 3. Agregar o Incrementar (Lógica Unificada)
        if cart_id not in self.carrito:
            self.carrito[cart_id] = {
                "producto_id": producto.id,
                "variante_id": variante.id if variante else None,
                "nombre": nombre_mostrar,
                "precio": str(precio_final),
                "cantidad": 1,
                "imagen": producto.imagen.url if producto.imagen else ""
            }
        else:
            self.carrito[cart_id]["cantidad"] += 1
        
        self.guardar()

    def guardar(self):
        self.session["carrito_ultimo_acceso"] = datetime.now().isoformat()
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def eliminar(self, producto, variante=None):
        if variante:
            cart_id = f"{producto.id}_{variante.id}"
        else:
            cart_id = str(producto.id)

        if cart_id in self.carrito:
            del self.carrito[cart_id]
            self.guardar()

    def restar(self, producto, variante=None):
        if variante:
            cart_id = f"{producto.id}_{variante.id}"
        else:
            cart_id = str(producto.id)

        if cart_id in self.carrito:
            self.carrito[cart_id]["cantidad"] -= 1
            if self.carrito[cart_id]["cantidad"] < 1:
                self.eliminar(producto, variante)
            else:
                self.guardar()

    def vaciar(self):
        self.session["carrito"] = {}
        if "carrito_ultimo_acceso" in self.session:
            del self.session["carrito_ultimo_acceso"]
        self.session.modified = True
    
    def obtener_total(self):
            total = Decimal("0.00")
            ids_a_eliminar = [] # Lista para limpiar productos que ya no existen en BD

            for cart_id, item in self.carrito.items():
                try:
                    # 1. Obtenemos el producto real de la BD
                    producto = Producto.objects.get(id=item["producto_id"])
                    
                    # 2. Determinamos el precio real actual
                    if producto.en_oferta and producto.precio_oferta:
                        precio_real = producto.precio_oferta
                    else:
                        precio_real = producto.precio
                    
                    # (Nota: Si las variantes tuvieran sobreprecio, aquí sumaríamos esa lógica)
                    
                    # 3. Sumamos al total
                    total += precio_real * item["cantidad"]
                    
                    # Opcional: Actualizamos el precio en la sesión para que el usuario lo vea actualizado
                    # en la lista de items sin recargar toda la lógica visual
                    item["precio"] = str(precio_real)

                except Producto.DoesNotExist:
                    # Si el producto fue borrado de la tienda, lo marcamos para quitar del carrito
                    ids_a_eliminar.append(cart_id)
            
            # Limpieza de items huerfanos
            if ids_a_eliminar:
                for cart_id in ids_a_eliminar:
                    del self.carrito[cart_id]
                self.guardar()

            return total
    
        
   