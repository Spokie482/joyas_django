#!/usr/bin/env bash
# Salir si hay error
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Recolectar archivos estáticos (CSS/JS)
python manage.py collectstatic --noinput

# Aplicar migraciones a la base de datos de producción
python manage.py migrate

# Crear superusuario automáticamente si no existe
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin_joyas').exists() or User.objects.create_superuser('marianlea', 'admin@ejemplo.com', 'joyas123')"