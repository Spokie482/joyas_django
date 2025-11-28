
# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    
class Perfil(models.Model):
    # Relación 1 a 1: Un usuario tiene UN solo perfil
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # Datos extra
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    direccion = models.CharField(max_length=150, blank=True, null=True, verbose_name="Dirección de Envío")
    ciudad = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ciudad")
    codigo_postal = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código Postal")
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True, verbose_name="Foto de Perfil")

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

# 2. LA SEÑAL (AUTOMATIZACIÓN)
@receiver(post_save, sender=User)
def crear_perfil_automatico(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(usuario=instance)

@receiver(post_save, sender=User)
def guardar_perfil_automatico(sender, instance, **kwargs):
    # Verificamos si existe el perfil antes de guardar para evitar errores raros
    if hasattr(instance, 'perfil'):
        instance.perfil.save()

class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Esto evita que un usuario le de like 2 veces al mismo producto
        unique_together = ('usuario', 'producto')

    def __str__(self):
        return f"{self.usuario.username} ❤️ {self.producto.nombre}"