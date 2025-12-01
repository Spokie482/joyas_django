from datetime import datetime, timedelta

class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        
        # 1. Intentamos obtener el carrito
        carrito = self.session.get("carrito")
        
        # 2. Verificamos expiración (2 HORAS)
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
        # Actualizamos la marca de tiempo al momento actual
        self.session["carrito_ultimo_acceso"] = datetime.now().isoformat()
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def eliminar(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.guardar() # Actualiza el reloj al eliminar también

    def restar(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            self.carrito[producto_id]["cantidad"] -= 1
            if self.carrito[producto_id]["cantidad"] < 1:
                self.eliminar(producto)
            else:
                self.guardar()

    def vaciar(self):
        self.session["carrito"] = {}
        if "carrito_ultimo_acceso" in self.session:
            del self.session["carrito_ultimo_acceso"]
        self.session.modified = True
        
    def obtener_total(self):
        total = 0
        for item in self.carrito.values():
            total += float(item["precio"]) * item["cantidad"]
        return total