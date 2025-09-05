from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

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
    
class Proyecto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    # 🔹 Nuevos campos
    avance = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Porcentaje de avance total del proyecto"
    )
    intervencion_total = models.PositiveIntegerField(
        default=0,
        help_text="Número total de intervenciones en el proyecto"
    )
    intervencion_rmbc = models.PositiveIntegerField(
        default=0,
        help_text="Número de intervenciones realizadas por RMBC"
    )
    ejecucion_proyecto = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Porcentaje de ejecución del proyecto"
    )
    ejecucion_financiera = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Monto de ejecución financiera en millones"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ["nombre"]

class Frente(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, blank=True, null=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ('nombre',)

    def __str__(self):
        return self.nombre


def get_default_frente():
    # Devuelve el Frente con id=1, o crea uno si no existe
    return Frente.objects.first().id if Frente.objects.exists() else None
class Reunion(models.Model):
    ESTADOS = [
        ('sin_iniciar', 'Sin iniciar'),
        ('en_proceso', 'En proceso'),
        ('cerrada', 'Cerrada'),
    ]

    proyecto = models.ForeignKey(
        'Proyecto',
        on_delete=models.CASCADE,
        related_name='reuniones',
        null=True,
        blank=True
    )
    frente = models.ForeignKey(
        'Frente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reuniones',
        default=get_default_frente
    )

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    fecha = models.DateTimeField(null=True, blank=True)   
    fecha_finalizacion = models.DateTimeField(null=True, blank=True) 

    estado = models.CharField(max_length=20, choices=ESTADOS, default='sin_iniciar')
    grupo_trabajo = models.ForeignKey(
        'GrupoTrabajo',
        on_delete=models.CASCADE,
        related_name='reuniones'
    )
    etiquetas = models.ManyToManyField('Etiqueta', blank=True, related_name="reuniones")
    documentos = models.ManyToManyField('Documento', blank=True, related_name="reuniones")

    responsables = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="reuniones_responsables"
    )

    def __str__(self):
        proyecto_nombre = getattr(self.proyecto, 'nombre', 'Sin proyecto')
        return f"{self.titulo} — {proyecto_nombre}"


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
