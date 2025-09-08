from django.contrib import admin
from .models import Reunion, Intervencion, Comentario, GrupoTrabajo, Etiqueta, Documento, IntervencionDocumento, Proyecto, Frente


@admin.register(GrupoTrabajo)
class GrupoTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    filter_horizontal = ('usuarios',)

@admin.register(Reunion)
class ReunionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'frente', 'estado')
    search_fields = ('titulo',)
    list_filter = ('estado', 'frente__tipo')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            qs = Reunion.objects.filter(frente__tipo='actividad')
            proyecto_id = request.GET.get('proyecto')
            if proyecto_id:
                qs = qs.filter(proyecto_id=proyecto_id)
            kwargs["queryset"] = qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Intervencion)
admin.site.register(Comentario)
admin.site.register(Etiqueta)
admin.site.register(Documento)
admin.site.register(IntervencionDocumento)
@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre','intervencion_total', 'intervencion_rmbc', 'ejecucion_proyecto', 'ejecucion_financiera')
    search_fields = ('nombre',)
    
admin.site.register(Frente)
