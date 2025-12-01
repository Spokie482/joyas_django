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

    def agregar(self, producto):
        # ... (Mantén tu lógica de agregar existente aquí) ...
        if producto.en_oferta and producto.precio_oferta:
            precio_final = producto.precio_oferta
        else:
            precio_final = producto.precio
        
        if str(producto.id) not in self.carrito:
            self.carrito[str(producto.id)] = {
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "precio": str(precio_final),
                "cantidad": 1,
                "imagen": producto.imagen.url if producto.imagen else ""
            }
        else:
            self.carrito[str(producto.id)]["cantidad"] += 1
        
        self.guardar() # Esto actualiza el reloj

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