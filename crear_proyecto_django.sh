#!/bin/bash

# Configuración
ROOT_DIR="mi_proyecto_django"
PROJECT_NAME="mi_proyecto"
APP_NAME="mi_aplicacion"

# Crear carpeta principal
mkdir "$ROOT_DIR"
cd "$ROOT_DIR" || exit

# Crear requirements.txt
cat <<EOF > requirements.txt
Django>=4.2,<5.0
EOF

# Crear Dockerfile
cat <<EOF > Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /code/
EOF

# Crear docker-compose.yml
cat <<EOF > docker-compose.yml
version: '3.9'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"
EOF

# Instalar dependencias para poder crear el proyecto (de manera temporal)
docker run --rm -v \$PWD:/code -w /code python:3.11-slim sh -c "pip install Django && django-admin startproject $PROJECT_NAME . && python manage.py startapp $APP_NAME"

# Crear urls.py dentro de la app
cat <<EOF > $APP_NAME/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
]
EOF

# Crear vista simple
cat <<EOF > $APP_NAME/views.py
from django.http import HttpResponse

def index(request):
    return HttpResponse("¡Hola desde $APP_NAME!")
EOF

echo "✅ Proyecto Django con estructura completa creado en: $ROOT_DIR"
echo "📌 Recuerda editar $PROJECT_NAME/settings.py para añadir '$APP_NAME' en INSTALLED_APPS"
echo "📌 Y conectar las URLs de $APP_NAME en $PROJECT_NAME/urls.py"
