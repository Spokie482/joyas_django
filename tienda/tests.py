from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from .carrito import Carrito
from datetime import datetime, timedelta
import time
from django.contrib.auth.models import User
from .models import Producto, Perfil, Orden, DetalleOrden

class ProductoModelTest(TestCase):
    def setUp(self):
        # Creamos un producto de prueba
        self.producto = Producto.objects.create(
            nombre="Anillo Test",
            precio=10000.00,
            categoria="AN",
            stock=5
        )

    def test_creacion_producto(self):
        """Prueba que el producto se guarde con los datos correctos"""
        self.assertEqual(self.producto.nombre, "Anillo Test")
        self.assertEqual(self.producto.stock, 5)
        self.assertEqual(str(self.producto), "Anillo Test - $10000.0")

class CarritoLogicTest(TestCase):
    def setUp(self):
        # Configuración para probar el Carrito (que depende de sesiones)
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        
        # Truco para activar sesiones en el test
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(self.request)
        self.request.session.save()
        
        # Producto para el carrito
        self.producto = Producto.objects.create(
            nombre="Collar Test", precio=5000, stock=10
        )

    def test_agregar_carrito(self):
        """Prueba agregar items y calcular total"""
        carrito = Carrito(self.request)
        carrito.agregar(self.producto)
        
        self.assertIn(str(self.producto.id), carrito.carrito)
        self.assertEqual(carrito.carrito[str(self.producto.id)]['cantidad'], 1)
        self.assertEqual(carrito.obtener_total(), 5000)

    def test_expiracion_carrito(self):
        """Prueba la lógica de las 2 horas (Tarea 2)"""
        carrito = Carrito(self.request)
        carrito.agregar(self.producto)
        
        # Simulamos que el último acceso fue hace 3 horas (manipulando la sesión)
        hace_tres_horas = datetime.now() - timedelta(hours=3)
        self.request.session["carrito_ultimo_acceso"] = hace_tres_horas.isoformat()
        self.request.session.save()
        
        # Al inicializar de nuevo el carrito, debería vaciarse
        carrito_nuevo = Carrito(self.request)
        
        # Verificamos que esté vacío
        self.assertEqual(len(carrito_nuevo.carrito), 0)

class PerfilSignalTest(TestCase):
    def test_perfil_creado_automaticamente(self):
        """Prueba que al crear un User, se cree su Perfil automáticamente"""
        # 1. Creamos un usuario
        user = User.objects.create_user(username='testuser', password='123')
        
        # 2. Verificamos si el perfil existe sin haberlo creado explícitamente
        self.assertTrue(hasattr(user, 'perfil'))
        self.assertIsInstance(user.perfil, Perfil)
        print("✅ Test Perfil Automático: OK")

class ProductoDatabaseTest(TestCase):
    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Anillo Test",
            precio=15000.00,
            categoria="AN",
            stock=10,
            en_oferta=True,
            precio_oferta=12000.00
        )

    def test_guardado_producto(self):
        """Prueba que los datos del producto se guarden correctamente en la BD"""
        producto_db = Producto.objects.get(id=self.producto.id)
        self.assertEqual(producto_db.nombre, "Anillo Test")
        self.assertEqual(producto_db.stock, 10)
        # Verificamos que el precio de oferta se guardó
        self.assertEqual(producto_db.precio_oferta, 12000.00)
        print("✅ Test Base de Datos Producto: OK")

class OrdenFlowTest(TestCase):
    def setUp(self):
        # Datos necesarios para una orden
        self.user = User.objects.create_user(username='comprador', password='123')
        self.producto = Producto.objects.create(nombre="Collar", precio=5000, stock=5)

    def test_creacion_orden_y_detalle(self):
        """Simula el proceso de crear una orden y sus detalles en la BD"""
        
        # 1. Crear la Orden (Cabecera)
        orden = Orden.objects.create(
            usuario=self.user,
            total=10000,
            estado='PAGADO',
            direccion='Calle Falsa 123'
        )
        
        # 2. Crear el Detalle (Items)
        detalle = DetalleOrden.objects.create(
            orden=orden,
            producto=self.producto,
            cantidad=2,
            precio_unitario=5000
        )
        
        # 3. Verificar Relaciones
        self.assertEqual(orden.items.count(), 1)
        self.assertEqual(orden.items.first().producto.nombre, "Collar")
        
        # 4. Simular Resta de Stock (Como lo hace la vista)
        self.producto.stock -= detalle.cantidad
        self.producto.save()
        
        # Verificar que el stock bajó en la base de datos
        producto_actualizado = Producto.objects.get(id=self.producto.id)
        self.assertEqual(producto_actualizado.stock, 3) # Tenía 5, compró 2 -> Quedan 3
        
        print("✅ Test Flujo de Orden y Stock: OK")
# Create your tests here.
