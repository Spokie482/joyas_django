class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        carrito = self.session.get("carrito")
        if not carrito:
            carrito = self.session["carrito"] = {}
        self.carrito = carrito

    def agregar(self, producto):
        if producto.en_oferta and producto.precio_oferta:
            precio_final = producto.precio_oferta
        else:
            precio_final = producto.precio
        
        if str(producto.id) not in self.carrito:
            self.carrito[str(producto.id)] = {
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "precio": str(precio_final), # Guardamos como string para evitar error JSON
                "cantidad": 1,
                "imagen": producto.imagen.url if producto.imagen else ""
            }
        else:
            self.carrito[str(producto.id)]["cantidad"] += 1
        self.guardar()

    def guardar(self):
        self.session.modified = True

    def eliminar(self, producto):
        producto_id = str(producto.id)
        if producto_id in self.carrito:
            del self.carrito[producto_id]
            self.guardar()

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
        self.session.modified = True
        
    def obtener_total(self):
        total = 0
        for item in self.carrito.values():
            total += float(item["precio"]) * item["cantidad"]
        return total