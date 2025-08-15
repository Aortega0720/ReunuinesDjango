# tu_app/urls.py
from django.urls import path
from .views import (
    ReunionListView, ReunionDetailView, ListaReunionesView,
    GraficoReunionesView, ExportarReunionesExcelView,
    SitioConstruccionView, ActaReunionPDFView,
    DocumentosView, ActasPorProyectoView
)

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
]

