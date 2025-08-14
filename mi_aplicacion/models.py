from django.db import models
from django.contrib.auth.models import User

class GrupoTrabajo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    usuarios = models.ManyToManyField(User, related_name='grupos_trabajo')

    def __str__(self):
        return self.nombre

class Etiqueta(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Documento(models.Model):
    archivo = models.FileField(upload_to='reuniones/documentos/')
    nombre = models.CharField(max_length=255, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre or self.archivo.name

class Reunion(models.Model):
    ESTADOS = [
        ('sin_iniciar', 'Sin iniciar'),
        ('en_proceso', 'En proceso'),
        ('cerrada', 'Cerrada'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='sin_iniciar')
    grupo_trabajo = models.ForeignKey(GrupoTrabajo, on_delete=models.CASCADE, related_name='reuniones')
    etiquetas = models.ManyToManyField(Etiqueta, blank=True, related_name="reuniones")
    documentos = models.ManyToManyField(Documento, blank=True, related_name="reuniones")

    def __str__(self):
        return self.titulo

class IntervencionDocumento(models.Model):
    intervencion = models.ForeignKey('Intervencion', on_delete=models.CASCADE, related_name='documentos')
    archivo = models.FileField(upload_to='documentos/intervenciones/', blank=True)
    nombre = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nombre or self.archivo.name


class Intervencion(models.Model):
    reunion = models.ForeignKey('Reunion', on_delete=models.CASCADE, related_name='intervenciones')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.autor.username} en {self.reunion.titulo}"
    

class Comentario(models.Model):
    intervencion = models.ForeignKey(Intervencion, related_name='comentarios', on_delete=models.CASCADE)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comentario de {self.autor} en {self.intervencion}'
