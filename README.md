Pasos para instalar Django con Docker

1. 📁 Crea una carpeta para tu proyecto
   mkdir mi_proyecto_django
   cd mi_proyecto_django
2. 📝 Crea un archivo Dockerfile

# Dockerfile
FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /code/

3. 📦 Crea un archivo requirements.txt

Django>=4.2,<5.0

4. ⚙️ Crea un archivo docker-compose.yml

version: '3.9'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"

5. 🚀 Inicializa el proyecto Django
docker-compose run web django-admin startproject core .

6. ▶️ Ejecuta el servidor
docker-compose up

🧼 Comandos útiles
Detener contenedores: docker-compose down
Reconstruir contenedor: docker-compose up --build
Ejecutar comandos dentro del contenedor:

docker-compose run web python manage.py migrate
docker-compose run web python manage.py createsuperuser