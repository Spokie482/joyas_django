
# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Categoria(models.Model):
    nombre = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, help_text="Identificador para la URL (ej: anillos-oro)")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='joyas/', null=True, blank=True)
    
    # El stock global se mantiene, pero la variante tendrá prioridad si existe
    stock = models.IntegerField(default=1)

    en_oferta = models.BooleanField(default=False, verbose_name="¿Está en Oferta?")
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Rebajado")

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"
    
class Variante(models.Model):
    producto = models.ForeignKey(Producto, related_name='variantes', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50, help_text="Ej: Talla S, Rojo, 15ml")
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre}"
    
class Cupon(models.Model):
    codigo = models.CharField(max_length=50, unique=True, help_text="Ej: VERANO2025")
    descuento = models.IntegerField(help_text="Porcentaje de descuento (0-100)")
    valido_desde = models.DateTimeField()
    valido_hasta = models.DateTimeField()
    activo = models.BooleanField(default=True)

    usuarios_usados = models.ManyToManyField(User, blank=True, related_name='cupones_usados')

    def __str__(self):
        return f"{self.codigo} - {self.descuento}% OFF"

class Orden(models.Model):
    
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Pago'),
        ('PAGADO', 'Pagado / En Preparación'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    # Relacionamos la orden con el usuario (Cliente)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')

    direccion = models.CharField(max_length=250, default="", verbose_name="Dirección")
    ciudad = models.CharField(max_length=100, default="", verbose_name="Ciudad")
    codigo_postal = models.CharField(max_length=20, default="", verbose_name="Código Postal")
    telefono = models.CharField(max_length=20, default="", verbose_name="Teléfono")
    
    def __str__(self):
        return f"Orden #{self.id} - {self.usuario.username} ({self.get_estado_display()})"

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
    
class Review(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='reviews')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    comentario = models.TextField(verbose_name="Tu opinión")
    calificacion = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="Estrellas")
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre} ({self.calificacion}★)"