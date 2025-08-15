# tu_app/views.py
from django.views.generic import ListView, DetailView, TemplateView
from .models import Reunion, Intervencion, Comentario, Proyecto,Frente
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import IntervencionForm, ComentarioForm, IntervencionDocumentoForm
from django.db.models import Count,Prefetch
from django.utils.dateparse import parse_date
from django.http import JsonResponse, HttpResponse
import openpyxl
from django.views import View

from itertools import groupby
from operator import attrgetter

class ReunionListView(ListView):
    model = Reunion
    template_name = 'mi_aplicacion/reunion_list.html'
    context_object_name = 'reuniones'
    paginate_by = 9  # ajustar si quieres más/menos por página

    def get_queryset(self):
        qs = (
            Reunion.objects
            .select_related('grupo_trabajo', 'proyecto', 'frente')
            .prefetch_related('etiquetas')
        ).order_by(
            'frente__nombre',  # ordenar por frente primero para el groupby
            '-fecha'
        )

        proyecto_pk = self.request.GET.get('proyecto')
        if proyecto_pk:
            try:
                qs = qs.filter(proyecto_id=int(proyecto_pk))
            except (ValueError, TypeError):
                pass

        # también filtrar por frente si se pasa (opcional)
        frente_pk = self.request.GET.get('frente')
        if frente_pk:
            try:
                qs = qs.filter(frente_id=int(frente_pk))
            except (ValueError, TypeError):
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Proyectos para el select
        context['proyectos'] = Proyecto.objects.order_by('nombre')
        context['proyecto_actual'] = self.request.GET.get('proyecto', '')
        context['frente_actual'] = self.request.GET.get('frente', '')

        # Agrupar las reuniones de la página actual por frente
        page_qs = context.get('page_obj').object_list if context.get('page_obj') else list(context.get('reuniones', []))

        # Normalizar nombre de frente (si None -> 'Sin frente')
        def frente_name(item):
            return item.frente.nombre if getattr(item, 'frente', None) else 'Sin frente'

        # `page_qs` ya viene ordenado por frente__nombre en get_queryset, por eso groupby funciona
        grouped = []
        for name, group in groupby(page_qs, key=frente_name):
            grouped.append({
                'frente': name,
                'reuniones': list(group),
                'count': sum(1 for _ in group)  # aunque ya consumimos group al list(group), keep count from list length
            })

        # Correction: above consumed group; better compute from list length:
        grouped = []
        for name, group in groupby(page_qs, key=frente_name):
            items = list(group)
            grouped.append({
                'frente': name,
                'reuniones': items,
                'count': len(items),
            })

        context['grouped_reuniones'] = grouped

        return context

class ReunionDetailView(LoginRequiredMixin, DetailView):
    model = Reunion
    template_name = 'mi_aplicacion/reunion_detail.html'
    context_object_name = 'reunion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_intervencion'] = IntervencionForm()
        context['form_documento'] = IntervencionDocumentoForm()  # ← Añadimos el formulario de documento
        context['comentario_forms'] = {
            intervencion.pk: ComentarioForm(prefix=str(intervencion.pk))
            for intervencion in self.object.intervenciones.all()
        }
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # 1️⃣ Manejar comentarios
        for intervencion in self.object.intervenciones.all():
            prefix = str(intervencion.pk)
            form = ComentarioForm(request.POST, prefix=prefix)
            if form.is_valid():
                comentario = form.save(commit=False)
                comentario.intervencion = intervencion
                comentario.autor = request.user
                comentario.save()
                return redirect('mi_aplicacion:reunion_detail', pk=self.object.pk)

        # 2️⃣ Manejar intervención nueva con documento
        form_intervencion = IntervencionForm(request.POST)
        form_documento = IntervencionDocumentoForm(request.POST, request.FILES)

        if form_intervencion.is_valid():
            intervencion = form_intervencion.save(commit=False)
            intervencion.reunion = self.object
            intervencion.autor = request.user
            intervencion.save()

            # Si hay documento, guardarlo
            if form_documento.is_valid() and form_documento.cleaned_data.get('archivo'):
                doc = form_documento.save(commit=False)
                doc.intervencion = intervencion
                doc.save()

            return redirect('mi_aplicacion:reunion_detail', pk=self.object.pk)

        # 3️⃣ Si algo falla, recargar la página con errores
        context = self.get_context_data()
        context['form_intervencion'] = form_intervencion
        context['form_documento'] = form_documento
        return self.render_to_response(context)
  
class ListaReunionesView(ListView):
    model = Reunion
    template_name = "mi_aplicacion/lista_reuniones_info.html"
    context_object_name = "reuniones"

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtros
        estado = self.request.GET.get("estado")
        proyecto = self.request.GET.get("proyecto")
        frente = self.request.GET.get("frente")

        if estado:
            queryset = queryset.filter(estado=estado)
        if proyecto:
            queryset = queryset.filter(proyecto_id=proyecto)
        if frente:
            queryset = queryset.filter(frente_id=frente)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["estado_actual"] = self.request.GET.get("estado", "")
        context["proyecto_actual"] = self.request.GET.get("proyecto", "")
        context["frente_actual"] = self.request.GET.get("frente", "")

        # Opciones disponibles para los select
        context["estados_disponibles"] = (
            Reunion.objects.values_list("estado", flat=True).distinct()
        )
        context["proyectos_disponibles"] = Proyecto.objects.all()
        context["frentes_disponibles"] = Frente.objects.all()

        return context


class GraficoReunionesView(TemplateView):
    template_name = "mi_aplicacion/grafico_reuniones.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener parámetros GET
        estado_filtro = self.request.GET.get('estado')
        grupo_filtro = self.request.GET.get('grupo')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')

        # Query base
        queryset = Reunion.objects.all()

        # Aplicar filtros
        if estado_filtro:
            queryset = queryset.filter(estado=estado_filtro)

        if grupo_filtro:
            queryset = queryset.filter(grupo=grupo_filtro)

        if fecha_inicio:
            fecha_inicio = parse_date(fecha_inicio)
            if fecha_inicio:
                queryset = queryset.filter(fecha__gte=fecha_inicio)

        if fecha_fin:
            fecha_fin = parse_date(fecha_fin)
            if fecha_fin:
                queryset = queryset.filter(fecha__lte=fecha_fin)

        # Calcular conteos filtrados
        conteos = (
            queryset
            .values('estado')
            .annotate(total=Count('id'))
        )

        estados = [c['estado'] for c in conteos]
        cantidades = [c['total'] for c in conteos]

        # Pasar datos al template
        context['estados'] = estados
        context['cantidades'] = cantidades

        # Para mantener los filtros en el formulario
        context['estado_filtro'] = estado_filtro or ''
        context['grupo_filtro'] = grupo_filtro or ''
        context['fecha_inicio'] = self.request.GET.get('fecha_inicio', '')
        context['fecha_fin'] = self.request.GET.get('fecha_fin', '')

        return context
    
class ExportarReunionesExcelView(View):
    def get(self, request, *args, **kwargs):
        # Filtrar por estado, proyecto y frente si vienen en la URL
        estado = request.GET.get("estado")
        proyecto_id = request.GET.get("proyecto")
        frente_id = request.GET.get("frente")

        reuniones = Reunion.objects.all()

        if estado:
            reuniones = reuniones.filter(estado=estado)
        if proyecto_id:
            reuniones = reuniones.filter(proyecto_id=proyecto_id)
        if frente_id:
            reuniones = reuniones.filter(frente_id=frente_id)

        # Crear libro y hoja
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reuniones"

        # Encabezados
        ws.append([
            "ID", "Título", "Proyecto", "Frente", "Grupo", 
            "Fecha", "Estado", "Etiquetas", "Descripción"
        ])

        # Filas con datos
        for r in reuniones:
            etiquetas_texto = ", ".join(str(e) for e in r.etiquetas.all())

            ws.append([
                r.id,
                r.titulo,
                r.proyecto.nombre if r.proyecto else "",
                r.frente.nombre if r.frente else "",
                r.grupo_trabajo.nombre if r.grupo_trabajo else "",
                r.fecha.strftime("%d/%m/%Y") if r.fecha else "",
                r.estado,
                etiquetas_texto,
                r.descripcion or ""
            ])

        # Preparar respuesta HTTP
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="reuniones.xlsx"'
        wb.save(response)
        return response
    
class SitioConstruccionView(View):
    template_name = "mi_aplicacion/construccion.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)