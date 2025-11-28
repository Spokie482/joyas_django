
# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Producto(models.Model):
    CATEGORIAS = [
        ('AN', 'Anillo'),
        ('CO', 'Collar'),
        ('PU', 'Pulsera'),
        ('AR', 'Aretes'),
    ]

    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2) # Ejemplo: 1500.50
    categoria = models.CharField(max_length=2, choices=CATEGORIAS, default='AN')
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='joyas/', null=True, blank=True) # <--- ¡Nuevo!
    stock = models.IntegerField(default=1)

    
    en_oferta = models.BooleanField(default=False, verbose_name="¿Está en Oferta?")
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Rebajado")
    
    
    
    
    def __str__(self):
        return f"{self.nombre} - ${self.precio}"
    

class Orden(models.Model):
    # Relacionamos la orden con el usuario (Cliente)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    direccion = models.CharField(max_length=250, default="", verbose_name="Dirección")
    ciudad = models.CharField(max_length=100, default="", verbose_name="Ciudad")
    codigo_postal = models.CharField(max_length=20, default="", verbose_name="Código Postal")
    telefono = models.CharField(max_length=20, default="", verbose_name="Teléfono")
    
    def __str__(self):
        return f"Orden #{self.id} - {self.usuario.username}"

class DetalleOrden(models.Model):
    # Esta tabla conecta la Orden con los Productos
    orden = models.ForeignKey(Orden, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"