# Configuración
$RootDir = "mi_proyecto_django"
$ProjectName = "mi_proyecto"
$AppName = "mi_aplicacion"

Write-Host "📁 Creando carpeta del proyecto: $RootDir"
New-Item -ItemType Directory -Path $RootDir -Force
Set-Location $RootDir

Write-Host "📝 Creando requirements.txt"
@"
Django>=4.2,<5.0
"@ | Out-File -Encoding utf8 requirements.txt

Write-Host "🐳 Creando Dockerfile"
@"
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /code/
"@ | Out-File -Encoding utf8 Dockerfile

Write-Host "⚙️  Creando docker-compose.yml"
@"
version: '3.9'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"
"@ | Out-File -Encoding utf8 docker-compose.yml

Write-Host "🐍 Inicializando entorno Django dentro de contenedor temporal..."

docker run --rm -v ${PWD}:/code -w /code python:3.11-slim `
    sh -c "pip install Django && django-admin startproject $ProjectName . && python manage.py startapp $AppName"

Write-Host "🗂️  Creando archivo urls.py dentro de la app"
@"
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
]
"@ | Out-File -Encoding utf8 "$AppName/urls.py"

Write-Host "👁️  Agregando vista de ejemplo en views.py"
@"
from django.http import HttpResponse

def index(request):
    return HttpResponse('¡Hola desde $AppName!')
"@ | Out-File -Encoding utf8 "$AppName/views.py"

Write-Host "✅ Proyecto Django creado exitosamente en '$RootDir'"
Write-Host "📌 Abre '$ProjectName/settings.py' y agrega '$AppName' a INSTALLED_APPS"
Write-Host "📌 Agrega las rutas de '$AppName' en '$ProjectName/urls.py'"
