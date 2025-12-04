from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

def comprimir_imagen(imagen, nuevo_ancho=800):
    """
    Recibe una imagen (InMemoryUploadedFile), la redimensiona y comprime.
    Retorna la imagen optimizada lista para guardar en el modelo.
    """
    # 1. Abrir la imagen usando Pillow
    img = Image.open(imagen)
    
    # 2. Convertir a RGB (necesario si la imagen es PNG con transparencia o CMYK)
    if img.mode in ('RGBA', 'P', 'CMYK'):
        img = img.convert('RGB')

    # 3. Calcular nueva altura manteniendo la proporción
    ancho_original, alto_original = img.size
    
    # Si la imagen ya es más chica que el objetivo, no la tocamos
    if ancho_original <= nuevo_ancho:
        return imagen

    ratio = nuevo_ancho / float(ancho_original)
    nuevo_alto = int(float(alto_original) * ratio)

    # 4. Redimensionar (Usamos LANCZOS para alta calidad)
    img = img.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)

    # 5. Guardar en memoria (BytesIO)
    output = BytesIO()
    # quality=85 es un estándar excelente: reduce peso sin perder nitidez visible
    img.save(output, format='JPEG', quality=85, optimize=True)
    output.seek(0)

    # 6. Crear el nuevo objeto de archivo para Django
    nueva_imagen = InMemoryUploadedFile(
        output,
        'ImageField',
        f"{imagen.name.split('.')[0]}.jpg", # Forzamos extensión .jpg
        'image/jpeg',
        sys.getsizeof(output),
        None
    )

    return nueva_imagen