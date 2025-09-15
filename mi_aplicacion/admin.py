import csv
from django.contrib import admin, messages
from django import forms
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import Reunion, Intervencion, Comentario, GrupoTrabajo, Etiqueta, Documento, IntervencionDocumento, Proyecto, Frente, GraphMailConfig

from .forms import UploadCSVForm
User = get_user_model()

# Desregistramos el UserAdmin original
admin.site.unregister(User)


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

# Formulario para subir CSV
class UploadCSVForm(forms.Form):
    csv_file = forms.FileField()

@admin.register(GraphMailConfig)
class GraphMailConfigAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email_send", "email_receive", "activo")

    def has_add_permission(self, request):
        """Evita mostrar el botón 'Add' si ya existe una configuración"""
        if GraphMailConfig.objects.exists():
            return False
        return True

    def changelist_view(self, request, extra_context=None):
        """
        Si ya existe una configuración, redirige al formulario de edición
        en vez de mostrar el listado.
        """
        config = GraphMailConfig.objects.first()
        if config:
            url = reverse("admin:mi_aplicacion_graphmailconfig_change", args=[config.pk])
            return redirect(url)
        return super().changelist_view(request, extra_context)

@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("username", "email")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-users-csv/",
                self.admin_site.admin_view(self.import_users_csv),
                name="import_users_csv",
            ),
        ]
        return custom_urls + urls

    def import_users_csv(self, request):
        """Vista dentro del admin para importar usuarios desde CSV"""
        if request.method == "POST":
            form = UploadCSVForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"].read().decode("utf-8").splitlines()
                reader = csv.DictReader(csv_file)

                count_new, count_skip = 0, 0

                for row in reader:
                    username = row.get("username")
                    email = row.get("email", "")
                    first_name = row.get("first_name", "")
                    last_name = row.get("last_name", "")
                    password = row.get("password", None)

                    if User.objects.filter(username=username).exists():
                        count_skip += 1
                        continue

                    user = User(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    if password:
                        user.set_password(password)
                    else:
                        user.set_unusable_password()

                    user.save()
                    count_new += 1

                self.message_user(
                    request,
                    f"✅ {count_new} usuarios creados. ⚠️ {count_skip} ya existían y se omitieron.",
                    level=messages.SUCCESS,
                )
                return redirect("..")  # vuelve a la lista de usuarios
        else:
            form = UploadCSVForm()

        context = {
            "form": form,
            "title": "Importar usuarios desde CSV",
        }
        return render(request, "admin/import_users_csv.html", context)

