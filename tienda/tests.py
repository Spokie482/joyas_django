from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from .models import Producto, Cupon, Orden, Review, Perfil, Favorito
from .views import ver_carrito, finalizar_compra
import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Producto, Cupon, Orden, Perfil, Favorito, Review
from django.contrib.sessions.middleware import SessionMiddleware
from datetime import datetime, timedelta
from .carrito import Carrito
from .forms import CheckoutForm, UserUpdateForm, PerfilUpdateForm, ReviewForm

class TiendaViewsTest(TestCase):
    
    def setUp(self):
        """Configuración inicial para todos los tests"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # Creamos productos de prueba
        self.producto1 = Producto.objects.create(
            nombre="Anillo Oro", precio=50000.00, stock=10, categoria='AN'
        )
        self.producto2 = Producto.objects.create(
            nombre="Collar Plata", precio=20000.00, stock=5, categoria='CO', en_oferta=True
        )
        
        # Creamos un cupón
        self.cupon = Cupon.objects.create(
            codigo="TEST10", descuento=10, 
            valido_desde=timezone.now(), valido_hasta=timezone.now() + timezone.timedelta(days=1)
        )

    # --- TEST CATÁLOGO Y BÚSQUEDA ---
    def test_catalogo_view(self):
        """Prueba que el catálogo cargue y muestre productos"""
        response = self.client.get(reverse('catalogo'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anillo Oro")
        self.assertTemplateUsed(response, 'tienda/index.html')

    def test_busqueda_ajax(self):
        """Prueba el buscador predictivo"""
        response = self.client.get(reverse('buscar_productos_ajax'), {'q': 'Anillo'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['resultados']), 1)
        self.assertEqual(data['resultados'][0]['nombre'], "Anillo Oro")

    # --- TEST CARRITO ---
    def test_agregar_carrito(self):
        """Prueba agregar un item al carrito"""
        url = reverse('agregar_carrito', args=[self.producto1.id])
        response = self.client.get(url) # Redirige al carrito
        
        # Verificamos que en la sesión esté el producto
        session = self.client.session
        self.assertIn(str(self.producto1.id), session['carrito'])
        self.assertEqual(session['carrito'][str(self.producto1.id)]['cantidad'], 1)

    def test_control_stock_carrito(self):
        """Prueba que no deje agregar más del stock disponible"""
        # Intentamos agregar 11 veces (stock es 10)
        for _ in range(11):
            self.client.get(reverse('agregar_carrito', args=[self.producto1.id]))
        
        session = self.client.session
        # Debería quedarse en 10
        self.assertEqual(session['carrito'][str(self.producto1.id)]['cantidad'], 10)

    def test_aplicar_cupon(self):
        """Prueba la aplicación de descuentos"""
        # 1. Agregamos producto al carrito ($50,000)
        self.client.get(reverse('agregar_carrito', args=[self.producto1.id]))
        
        # 2. Aplicamos cupón
        response = self.client.post(reverse('aplicar_cupon'), {'codigo_cupon': 'TEST10'})
        
        # 3. Verificamos que se guardó en sesión
        session = self.client.session
        self.assertEqual(session['cupon_id'], self.cupon.id)

    # --- TEST COMPRA ---
    def test_finalizar_compra_sin_login(self):
        """Debe redirigir al login si no estás autenticado"""
        response = self.client.get(reverse('finalizar_compra'))
        self.assertNotEqual(response.status_code, 200) # Redirección (302)

    def test_finalizar_compra_flow(self):
        """Prueba el flujo completo de compra"""
        self.client.login(username='testuser', password='password123')
        
        # 1. Llenar carrito
        self.client.get(reverse('agregar_carrito', args=[self.producto1.id]))
        
        # 2. Enviar formulario de checkout
        datos_checkout = {
            'direccion': 'Calle Falsa 123',
            'ciudad': 'Springfield',
            'codigo_postal': '1234',
            'telefono': '555555'
        }
        response = self.client.post(reverse('finalizar_compra'), datos_checkout)
        
        # 3. Verificar que se creó la orden
        self.assertEqual(Orden.objects.count(), 1)
        orden = Orden.objects.first()
        self.assertEqual(orden.total, 50000.00) # Precio sin envío (supera límite)
        
        # 4. Verificar que se restó el stock
        producto_actualizado = Producto.objects.get(id=self.producto1.id)
        self.assertEqual(producto_actualizado.stock, 9) # 10 - 1

    # --- TEST RESEÑAS ---
    def test_crear_review(self):
        self.client.login(username='testuser', password='password123')
        
        datos_review = {
            'calificacion': 5,
            'comentario': 'Excelente producto'
        }
        
        url = reverse('detalle', args=[self.producto1.id])
        self.client.post(url, datos_review)
        
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.first().calificacion, 5)

    # --- TEST DASHBOARD (SEGURIDAD) ---
    def test_dashboard_acceso_denegado(self):
        """Usuario normal NO debe poder entrar al dashboard"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('dashboard_admin'))
        # Debería redirigir al login de admin o dar error, no entrar (200)
        self.assertNotEqual(response.status_code, 200)

class ProductoModelTest(TestCase):
    def test_crear_producto(self):
        producto = Producto.objects.create(
            nombre="Anillo de Prueba",
            precio=15000.50,
            categoria="AN",
            stock=10,
            en_oferta=True,
            precio_oferta=12000.00
        )
        self.assertEqual(producto.nombre, "Anillo de Prueba")
        self.assertEqual(producto.stock, 10)
        self.assertTrue(producto.en_oferta)
        self.assertEqual(str(producto), "Anillo de Prueba - $15000.5")

class CuponModelTest(TestCase):
    def test_crear_cupon(self):
        cupon = Cupon.objects.create(
            codigo="TEST20",
            descuento=20,
            valido_desde=timezone.now(),
            valido_hasta=timezone.now() + timezone.timedelta(days=30)
        )
        self.assertEqual(str(cupon), "TEST20 - 20% OFF")
        self.assertTrue(cupon.activo)

class OrdenModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cliente', password='123')

    def test_crear_orden(self):
        orden = Orden.objects.create(
            usuario=self.user,
            total=5000.00,
            estado='PENDIENTE',
            ciudad="Buenos Aires"
        )
        self.assertEqual(orden.usuario, self.user)
        self.assertEqual(orden.estado, 'PENDIENTE')
        self.assertEqual(str(orden), f"Orden #{orden.id} - cliente (Pendiente de Pago)")

class PerfilSignalTest(TestCase):
    def test_perfil_automatico(self):
        """Verifica que al crear un User, se crea su Perfil automáticamente"""
        nuevo_usuario = User.objects.create_user(username='nuevo', password='123')
        
        # Intentamos acceder al perfil
        self.assertTrue(hasattr(nuevo_usuario, 'perfil'))
        self.assertIsInstance(nuevo_usuario.perfil, Perfil)
        
        # Probamos guardar datos en el perfil
        nuevo_usuario.perfil.telefono = "1122334455"
        nuevo_usuario.perfil.save()
        
        self.assertEqual(Perfil.objects.get(usuario=nuevo_usuario).telefono, "1122334455")

class FavoritoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='fan', password='123')
        self.producto = Producto.objects.create(nombre="Joya", precio=100)

    def test_favorito_unico(self):
        # Creamos el primer favorito
        Favorito.objects.create(usuario=self.user, producto=self.producto)
        
        # Intentar crear el mismo favorito debería fallar (IntegrityError)
        # Nota: En SQLite a veces no lanza el error inmediatamente en tests simples sin transaction,
        # pero verificamos que unique_together esté en Meta.
        with self.assertRaises(Exception):
            Favorito.objects.create(usuario=self.user, producto=self.producto)



class PruebasLogicaCarrito(TestCase):
    def setUp(self):
        # 1. Configuración inicial (Se ejecuta antes de cada test)
        # Creamos una petición web falsa (RequestFactory) para simular un usuario
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        
        # Truco técnico: Agregamos soporte de sesiones a la petición falsa
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(self.request)
        self.request.session.save()

        # 2. Creamos Productos de prueba en la Base de Datos temporal
        self.prod_normal = Producto.objects.create(
            nombre="Anillo Simple", 
            precio=1000.00, 
            stock=10,
            en_oferta=False
        )
        
        self.prod_oferta = Producto.objects.create(
            nombre="Collar Oferta", 
            precio=2000.00, 
            stock=5,
            en_oferta=True,
            precio_oferta=1500.00 # Precio real que debe cobrar
        )

    def test_agregar_y_calcular_total(self):
        """Prueba que suma bien los precios y cantidades"""
        carrito = Carrito(self.request)
        
        # Agregamos 2 anillos normales (1000 c/u)
        carrito.agregar(self.prod_normal)
        carrito.agregar(self.prod_normal)
        
        # Verificamos cantidad
        item_id = str(self.prod_normal.id)
        self.assertEqual(carrito.carrito[item_id]['cantidad'], 2)
        
        # Verificamos el total (2 * 1000 = 2000)
        self.assertEqual(carrito.obtener_total(), 2000.00)

    def test_precio_oferta(self):
        """Prueba que detecte el precio de oferta si corresponde"""
        carrito = Carrito(self.request)
        carrito.agregar(self.prod_oferta)
        
        item_id = str(self.prod_oferta.id)
        # El precio guardado debe ser 1500 (oferta), no 2000
        self.assertEqual(float(carrito.carrito[item_id]['precio']), 1500.00)

    def test_restar_y_eliminar(self):
        """Prueba la lógica de restar items"""
        carrito = Carrito(self.request)
        carrito.agregar(self.prod_normal) # Cantidad 1
        carrito.agregar(self.prod_normal) # Cantidad 2
        
        # Restamos 1 -> Queda 1
        carrito.restar(self.prod_normal)
        item_id = str(self.prod_normal.id)
        self.assertEqual(carrito.carrito[item_id]['cantidad'], 1)
        
        # Restamos 1 más -> Se elimina del carrito
        carrito.restar(self.prod_normal)
        self.assertNotIn(item_id, carrito.carrito)

    def test_expiracion_2_horas(self):
        """Prueba CRÍTICA: El carrito debe vaciarse si pasaron 2 horas"""
        # 1. Iniciamos carrito y agregamos algo
        carrito = Carrito(self.request)
        carrito.agregar(self.prod_normal)
        self.assertTrue(len(carrito.carrito) > 0) # Confirmamos que tiene cosas
        
        # 2. SIMULAMOS EL PASO DEL TIEMPO (Hackeamos la sesión)
        # Le decimos que la última vez que entró fue hace 3 horas
        hace_tres_horas = datetime.now() - timedelta(hours=3)
        self.request.session["carrito_ultimo_acceso"] = hace_tres_horas.isoformat()
        self.request.session.save()
        
        # 3. Reiniciamos la clase Carrito (como si el usuario recargara la página)
        carrito_nuevo = Carrito(self.request)
        
        # 4. Verificación: El carrito nuevo debe estar vacío
        self.assertEqual(len(carrito_nuevo.carrito), 0)

    def test_no_expira_antes_de_tiempo(self):
        """Prueba de control: Si pasó 1 hora, NO debe borrarse"""
        carrito = Carrito(self.request)
        carrito.agregar(self.prod_normal)
        
        # Simulamos que pasó solo 1 hora
        hace_una_hora = datetime.now() - timedelta(hours=1)
        self.request.session["carrito_ultimo_acceso"] = hace_una_hora.isoformat()
        self.request.session.save()
        
        carrito_nuevo = Carrito(self.request)
        
        # Debe seguir teniendo el producto
        self.assertEqual(len(carrito_nuevo.carrito), 1)



class FormsTest(TestCase):
    
    def test_checkout_form_valido(self):
        """Prueba que el formulario de Checkout acepte datos correctos"""
        form_data = {
            'direccion': 'Av. Siempre Viva 742',
            'ciudad': 'Springfield',
            'codigo_postal': '1234',
            'telefono': '1122334455'
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_checkout_form_invalido(self):
        """Prueba que falle si falta un campo obligatorio (ej: dirección)"""
        form_data = {
            'direccion': '', # Campo vacío
            'ciudad': 'Springfield',
            'codigo_postal': '1234',
            'telefono': '1122334455'
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('direccion', form.errors)

    def test_user_update_form_email_valido(self):
        """Prueba la validación de formato de email"""
        form_data = {
            'first_name': 'Homero',
            'last_name': 'Simpson',
            'email': 'homero@ejemplo.com' # Email válido
        }
        form = UserUpdateForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_user_update_form_email_invalido(self):
        """Prueba que rechace emails mal formados"""
        form_data = {
            'first_name': 'Homero',
            'last_name': 'Simpson',
            'email': 'no-soy-un-email' # Email inválido
        }
        form = UserUpdateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_review_form_calificacion(self):
        """Prueba el formulario de reseñas"""
        # Caso válido
        form = ReviewForm(data={'calificacion': 5, 'comentario': 'Excelente!'})
        self.assertTrue(form.is_valid())
        
        # Caso inválido (falta calificación)
        form_invalido = ReviewForm(data={'calificacion': '', 'comentario': 'Malo'})
        self.assertFalse(form_invalido.is_valid())