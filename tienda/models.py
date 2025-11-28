
# Create your models here.
from django.db import models

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

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"