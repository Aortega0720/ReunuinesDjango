# tu_app/urls.py
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from .views import (
    ReunionListView, ReunionDetailView, ListaReunionesView,
    GraficoReunionesView, ExportarReunionesExcelView,
    SitioConstruccionView, ActaReunionPDFView,
    DocumentosView, ActasPorProyectoView,HomeView,ExportarProyectoPDF, ProyectoListView,
    ProyectoDetailView, ProyectoCreateView, ProyectoUpdateView, ProyectoDeleteView
)
# from mozilla_django_oidc import views as oidc_views

app_name = 'mi_aplicacion'

urlpatterns = [
    path('reuniones/', ReunionListView.as_view(), name='reunion_list'),
    path('reuniones/<int:pk>/', ReunionDetailView.as_view(), name='reunion_detail'),
    path("reuniones/informe/", ListaReunionesView.as_view(), name="lista_reuniones_info"),
    path('reuniones/grafico/', GraficoReunionesView.as_view(), name='grafico_reuniones'),
    path("exportar_excel/", ExportarReunionesExcelView.as_view(), name="exportar_excel"),
    path('construccion/', SitioConstruccionView.as_view(), name='sitio_construccion'),
    path('acta/<int:pk>/pdf/', ActaReunionPDFView.as_view(), name='acta_pdf'),
    path('documentos/', DocumentosView.as_view(), name='documentos'),
    path('actas/', ActasPorProyectoView.as_view(), name='actas_por_proyecto'),
    path('', HomeView.as_view(), name='home'),
    path('proyecto/<int:pk>/exportar_pdf/', ExportarProyectoPDF.as_view(), name='exportar_proyecto_pdf'),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="mi_aplicacion/login.html"),
        name="login",
    ),
    # path('oidc/authenticate/', oidc_views.OIDCAuthenticationRequestView.as_view(), name='oidc_authentication_init'),
    # path('oidc/callback/', oidc_views.OIDCAuthenticationCallbackView.as_view(), name='oidc_authentication_callback'),
    # path('oidc/logout/', oidc_views.OIDCLogoutView.as_view(), name='oidc_logout'),

    path('proyectos/', ProyectoListView.as_view(), name='proyecto_list'),
    path('proyectos/<int:pk>/', ProyectoDetailView.as_view(), name='proyecto_detail'),
    path('proyectos/nuevo/', ProyectoCreateView.as_view(), name='proyecto_create'),
    path('proyectos/<int:pk>/editar/', ProyectoUpdateView.as_view(), name='proyecto_update'),
    path('proyectos/<int:pk>/eliminar/', ProyectoDeleteView.as_view(), name='proyecto_delete'),
]

