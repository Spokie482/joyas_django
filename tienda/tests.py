# --- IMPORTACIONES NECESARIAS PARA LOS TESTS DE CONCURRENCIA ---
import threading
import time
from django.test import TransactionTestCase, Client
from django.db import connection
from django.urls import reverse
from django.contrib.auth.models import User
from tienda.models import Producto, Orden

# --- CLASE DE PRUEBAS DE RIESGO ---
class PruebasDeRiesgoStock(TransactionTestCase):
    """
    Tests diseñados específicamente para exponer vulnerabilidades 
    en la gestión de inventario (Stock) usando transacciones reales.
    """
    
    def setUp(self):
        # Limpiamos datos previos para asegurar un entorno limpio
        User.objects.filter(username__in=['comprador_a', 'comprador_b']).delete()
        Producto.objects.filter(nombre="Anillo Único").delete()

        # 1. Crear un producto crítico con 1 sola unidad de stock
        self.producto_critico = Producto.objects.create(
            nombre="Anillo Único",
            precio=1000.00,
            stock=1,
            categoria=None  # O ajusta según tu modelo si categoría es obligatoria
        )
        
        # 2. Crear dos usuarios compradores
        self.user_a = User.objects.create_user(username='comprador_a', password='123')
        self.user_b = User.objects.create_user(username='comprador_b', password='123')

    def test_escenario_1_stock_negativo(self):
        """
        ESCENARIO 1: Venta de producto sin stock.
        Simula que el stock se agota MIENTRAS el usuario A está pagando.
        """
        print("\n--- Iniciando Test: Stock Negativo ---")
        
        # 1. El usuario A llena su carrito
        self.client.login(username='comprador_a', password='123')
        self.client.get(reverse('agregar_carrito', args=[self.producto_critico.id]))
        
        # 2. SIMULACIÓN: Alguien más compra el producto en ese instante (Backdoor)
        # Forzamos el stock a 0 directamente en la BD simulando una venta externa
        self.producto_critico.stock = 0
        self.producto_critico.save()
        print(f"Stock forzado a 0 antes del pago de A.")

        # 3. El usuario A intenta pagar
        # (Si la vista NO verifica stock al momento de pagar, restará 1 a 0)
        datos_checkout = {
            'direccion': 'Calle A', 'ciudad': 'C', 
            'codigo_postal': '1', 'telefono': '1'
        }
        self.client.post(reverse('finalizar_compra'), datos_checkout)
        
        # 4. Verificación
        self.producto_critico.refresh_from_db()
        print(f"Stock final después del pago: {self.producto_critico.stock}")
        
        # Si el stock es -1, el test PASA (porque confirma la vulnerabilidad)
        # Si el stock es 0, el test FALLA (significa que el código ya es seguro)
        if self.producto_critico.stock < 0:
            print(">>> VULNERABILIDAD CONFIRMADA: Stock negativo generado.")
        
        self.assertTrue(self.producto_critico.stock < 0, "El sistema debería haber fallado permitiendo stock negativo (-1).")

    def test_escenario_2_condicion_de_carrera(self):
        """
        ESCENARIO 2: Condición de Carrera (Race Condition).
        Dos hilos compran el MISMO y ÚLTIMO ítem simultáneamente.
        """
        print("\n--- Iniciando Test: Condición de Carrera ---")
        
        # Función auxiliar que ejecutará cada hilo
        def comprar_producto(username, producto_id):
            # Creamos un cliente nuevo para cada hilo (simula navegadores distintos)
            cliente_hilo = Client()
            cliente_hilo.login(username=username, password='123')
            
            # Agregar al carrito
            cliente_hilo.get(reverse('agregar_carrito', args=[producto_id]))
            
            # Pagar
            datos = {'direccion': 'X', 'ciudad': 'X', 'codigo_postal': '1', 'telefono': '1'}
            cliente_hilo.post(reverse('finalizar_compra'), datos)
            
            # Importante: Cerrar conexión de este hilo para evitar errores de Django en tests
            connection.close()

        # 1. Preparamos los dos hilos
        hilo_1 = threading.Thread(target=comprar_producto, args=('comprador_a', self.producto_critico.id))
        hilo_2 = threading.Thread(target=comprar_producto, args=('comprador_b', self.producto_critico.id))

        # 2. ¡Disparo simultáneo!
        hilo_1.start()
        hilo_2.start()

        # 3. Esperamos a que terminen
        hilo_1.join()
        hilo_2.join()

        # 4. Análisis
        self.producto_critico.refresh_from_db()
        ordenes_totales = Orden.objects.filter(usuario__username__in=['comprador_a', 'comprador_b']).count()
        
        print(f"Stock inicial: 1")
        print(f"Órdenes generadas: {ordenes_totales}")
        print(f"Stock final: {self.producto_critico.stock}")

        # La vulnerabilidad se confirma si:
        # a) El stock quedó negativo (se restó dos veces 1 a 1 -> -1)
        # b) O se vendieron 2 productos (ordenes_totales > 1) cuando solo había 1
        es_vulnerable = (self.producto_critico.stock < 0) or (ordenes_totales > 1)
        
        if es_vulnerable:
            print(">>> VULNERABILIDAD CONFIRMADA: Sobreventa detectada.")

        self.assertTrue(es_vulnerable, "El sistema permitió vender más productos de los que existían.")