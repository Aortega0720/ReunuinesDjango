from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError

from decimal import Decimal, ROUND_HALF_UP
from datetime import date

User.add_to_class("__str__", lambda self: f"{self.first_name} {self.last_name}".strip() or self.username)

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

    # avance = models.DecimalField(
    #     max_digits=5, decimal_places=2, default=0,
    #     help_text="Porcentaje de avance total del proyecto"
    # )
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

    @property
    def avance_calculado(self):

        if not self.fecha_inicio or not self.fecha_fin:
            return 0

        inicio = self.fecha_inicio
        fin = self.fecha_fin
        hoy = date.today()

        total_dias = (fin - inicio).days
        if total_dias <= 0:
            return 100 if hoy >= fin else 0

        dias_transcurridos = (hoy - inicio).days
        porcentaje = (dias_transcurridos / total_dias) * 100

        return max(0, min(100, round(porcentaje, 2)))   

class Frente(models.Model):
    TIPOS = [
        ('actividad', 'Actividad'),
        ('tarea', 'Tarea'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, blank=True, null=True)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='actividad')
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

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tareas'
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

    def clean(self):
        super().clean()

        if self.parent:
            if self.parent_id == self.id:
                raise ValidationError("Una reunión no puede ser su propia actividad padre.")

            # parent debe tener frente y su tipo debe ser 'actividad'
            if not getattr(self.parent, "frente", None):
                raise ValidationError({"parent": "La actividad padre no tiene frente asignado."})

            if getattr(self.parent.frente, "tipo", None) != 'actividad':
                raise ValidationError({"parent": "El padre seleccionado no es una actividad (frente.tipo != 'actividad')."})

            # si ambos tienen proyecto, deben coincidir
            if self.proyecto and self.parent.proyecto and self.proyecto != self.parent.proyecto:
                raise ValidationError({"parent": "La actividad padre debe pertenecer al mismo proyecto que la tarea."})

    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        proyecto_nombre = getattr(self.proyecto, 'nombre', 'Sin proyecto')
        return f"{self.titulo} — {proyecto_nombre}"

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


class GraphMailConfig(models.Model):
    nombre = models.CharField(
        max_length=100,
        default="Configuración Principal",
        help_text="Identificador de la configuración."
    )
    tenant_id = models.CharField(max_length=200)
    client_id = models.CharField(max_length=200)
    client_secret = models.CharField(max_length=500)
    scope = models.CharField(max_length=300, default="https://graph.microsoft.com/.default")
    grant_type = models.CharField(max_length=100, default="client_credentials")

    email_send = models.EmailField(help_text="Correo desde el que se envía (ej: respuesta@regionmetropolitana.gov.co)")
    email_receive = models.EmailField(help_text="Correo de destino (ej: ortegaarrieta@gmail.com)")

    activo = models.BooleanField(default=True, help_text="Si está activo se usará esta configuración.")

    def __str__(self):
        return f"Config: {self.nombre} (send: {self.email_send})"

    class Meta:
        verbose_name = "Configuración Graph Mail"
        verbose_name_plural = "Configuraciones Graph Mail"

class KeycloakProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kc_profile")
    keycloak_id = models.CharField("Keycloak ID (sub)", max_length=255, unique=True, db_index=True)
    id_token = models.TextField(null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"KCProfile(user={self.user_id}, keycloak_id={self.keycloak_id})"