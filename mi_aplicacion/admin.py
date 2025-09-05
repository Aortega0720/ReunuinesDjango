from django.contrib import admin
from .models import Reunion, Intervencion, Comentario, GrupoTrabajo, Etiqueta, Documento, IntervencionDocumento, Proyecto, Frente


@admin.register(GrupoTrabajo)
class GrupoTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    filter_horizontal = ('usuarios',)

@admin.register(Reunion)
class ReunionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'estado', 'fecha', 'fecha_finalizacion', 'grupo_trabajo')

admin.site.register(Intervencion)
admin.site.register(Comentario)
admin.site.register(Etiqueta)
admin.site.register(Documento)
admin.site.register(IntervencionDocumento)
@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'avance', 'intervencion_total', 'intervencion_rmbc', 'ejecucion_proyecto', 'ejecucion_financiera')
    search_fields = ('nombre',)
    
admin.site.register(Frente)
