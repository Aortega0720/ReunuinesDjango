# stdlib
import os
from datetime import date, datetime, timedelta
from itertools import groupby
from operator import attrgetter

# Django
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.staticfiles import finders
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, CreateView, UpdateView, DeleteView

# terceros
import openpyxl
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (Image, ListFlowable, ListItem, PageBreak,
                                Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

# local (app)
from .forms import ComentarioForm, IntervencionDocumentoForm, IntervencionForm
from .models import Comentario, Frente, Intervencion, Proyecto, Reunion


class ReunionListView(ListView):
    model = Reunion
    template_name = 'mi_aplicacion/reunion_list.html'
    context_object_name = 'reuniones'
    paginate_by = 9

    def get_queryset(self):
        qs = (
            Reunion.objects
            .select_related('grupo_trabajo', 'proyecto', 'frente')
            .prefetch_related('etiquetas', 'responsables')
        ).order_by(
            'frente__nombre', 
            '-fecha'
        )

        # Filtro por proyecto
        proyecto_pk = self.request.GET.get('proyecto')
        if proyecto_pk:
            try:
                qs = qs.filter(proyecto_id=int(proyecto_pk))
            except (ValueError, TypeError):
                pass

        # Filtro por frente
        frente_pk = self.request.GET.get('frente')
        if frente_pk:
            try:
                qs = qs.filter(frente_id=int(frente_pk))
            except (ValueError, TypeError):
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Proyectos para el filtro
        context['proyectos'] = Proyecto.objects.order_by('nombre')
        context['proyecto_actual'] = self.request.GET.get('proyecto', '')
        context['frente_actual'] = self.request.GET.get('frente', '')

        # Agrupar reuniones de la página actual por frente
        page_qs = context.get('page_obj').object_list if context.get('page_obj') else list(context.get('reuniones', []))

        today = date.today()

        # Enriquecer cada reunión con estado y días restantes
        for reunion in page_qs:
            if reunion.fecha_finalizacion:
                diff = (reunion.fecha_finalizacion.date() - today).days
                reunion.dias_restantes = abs(diff)  
                reunion.estado_vencida = diff < 0
            else:
                reunion.dias_restantes = None
                reunion.estado_vencida = False

        def frente_name(item):
            return item.frente.nombre if getattr(item, 'frente', None) else 'Sin frente'

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
        reunion = self.object
        today = date.today()

        # 🔹 Calcular estado y días restantes
        if reunion.fecha_finalizacion:
            diff = (reunion.fecha_finalizacion.date() - today).days
            reunion.dias_restantes = abs(diff)  # se usa abs para mostrar días positivos
            reunion.estado_vencida = diff < 0
        else:
            reunion.dias_restantes = None
            reunion.estado_vencida = False

        # 🔹 Formularios
        context['form_intervencion'] = IntervencionForm()
        context['form_documento'] = IntervencionDocumentoForm()
        context['comentario_forms'] = {
            intervencion.pk: ComentarioForm(prefix=str(intervencion.pk))
            for intervencion in reunion.intervenciones.all()
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
        queryset = super().get_queryset().select_related("proyecto", "frente", "grupo_trabajo")

        # Capturar filtros del request
        estado = self.request.GET.get("estado")
        proyecto = self.request.GET.get("proyecto")
        frente = self.request.GET.get("frente")

        if estado:
            queryset = queryset.filter(estado=estado)
        if proyecto:
            queryset = queryset.filter(proyecto_id=proyecto)
        if frente:
            queryset = queryset.filter(frente_id=frente)

        # Calcular días restantes o vencido
        hoy = date.today()
        for reunion in queryset:
            if reunion.fecha_finalizacion:
                diferencia = (reunion.fecha_finalizacion.date() - hoy).days
                reunion.dias_restantes = abs(diferencia) if diferencia < 0 else diferencia
                reunion.vencido = diferencia < 0
            else:
                reunion.dias_restantes = None
                reunion.vencido = None

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Valores disponibles para los select
        context["estados_disponibles"] = [e[0] for e in Reunion.ESTADOS]  # ejemplo: ["pendiente", "en_progreso", "cerrada"]
        context["proyectos_disponibles"] = Proyecto.objects.all()
        context["frentes_disponibles"] = Frente.objects.all()

        # Mantener selección actual
        context["estado_actual"] = self.request.GET.get("estado", "")
        context["proyecto_actual"] = self.request.GET.get("proyecto", "")
        context["frente_actual"] = self.request.GET.get("frente", "")

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
        ws.title = "Actividades"

        # Encabezados
        ws.append([
            "ID", "Título", "Proyecto", "Frente", "Grupo",
            "Fecha Inicio", "Fecha Finalización", "Estado",
            "Etiquetas", "Descripción", "Vencido", "Tiempo Restante"
        ])

        # Filas con datos
        for r in reuniones:
            etiquetas_texto = ", ".join(str(e) for e in r.etiquetas.all())

            # Valores por defecto
            vencido = "N/A"
            tiempo_texto = ""

            if r.fecha_finalizacion:
                dias_restantes = (r.fecha_finalizacion.date() - date.today()).days

                if dias_restantes < 0:
                    vencido = "Sí"
                    tiempo_texto = f"Vencido hace {abs(dias_restantes)} días"
                elif dias_restantes == 0:
                    vencido = "No"
                    tiempo_texto = "Vence hoy"
                else:
                    vencido = "No"
                    tiempo_texto = f"Faltan {dias_restantes} días"

            ws.append([
                r.id,
                r.titulo,
                r.proyecto.nombre if r.proyecto else "",
                r.frente.nombre if r.frente else "",
                r.grupo_trabajo.nombre if r.grupo_trabajo else "",
                r.fecha.strftime("%d/%m/%Y") if r.fecha else "",
                r.fecha_finalizacion.strftime("%d/%m/%Y") if r.fecha_finalizacion else "",
                r.estado,
                etiquetas_texto,
                r.descripcion or "",
                vencido,
                tiempo_texto,
            ])

        # Preparar respuesta HTTP
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="Actividades.xlsx"'
        wb.save(response)
        return response
    
class SitioConstruccionView(View):
    template_name = "mi_aplicacion/construccion.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
    
class ActaReunionPDFView(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            reunion = Reunion.objects.get(pk=pk)
        except Reunion.DoesNotExist:
            raise Http404("La reunión no existe")

        # Configuración del PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Informe_{reunion.id}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=5*cm, bottomMargin=3*cm)
        styles = getSampleStyleSheet()
        elementos = []

        # Estilos personalizados
        estilo_intervencion = ParagraphStyle(
            name="Intervencion",
            fontSize=10,
            leading=14,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )

        estilo_comentario = ParagraphStyle(
            name="Comentario",
            fontSize=10,
            leading=12,
            leftIndent=1*cm,
            spaceAfter=4,
            alignment=TA_JUSTIFY,
            fontName="Helvetica-Oblique"
        )

        # Función para header y footer
        def header_footer(canvas, doc):
            banner_path = finders.find('img/banner.png')
            if banner_path:
                canvas.drawImage(banner_path, x=0, y=A4[1]-4*cm, width=A4[0], height=3*cm)
            footer_path = finders.find('img/footer.png')
            if footer_path:
                canvas.drawImage(footer_path, x=0, y=0, width=A4[0], height=2*cm)

        # Encabezado del contenido
        elementos.append(Spacer(1, 12))
        elementos.append(Paragraph("<b>Informe de actividad</b>", styles["Title"]))
        elementos.append(Spacer(1, 12))

        # Datos generales
        elementos.append(Paragraph(f"<b>Título:</b> {reunion.titulo}", styles["Normal"]))
        elementos.append(Paragraph(f"<b>Fecha:</b> {reunion.fecha.strftime('%d/%m/%Y')}", styles["Normal"]))
        elementos.append(Paragraph(f"<b>Proyecto:</b> {reunion.proyecto.nombre if reunion.proyecto else ''}", styles["Normal"]))
        elementos.append(Paragraph(f"<b>Frente:</b> {reunion.frente.nombre if reunion.frente else ''}", styles["Normal"]))
        elementos.append(Paragraph(f"<b>Estado:</b> {reunion.estado}", styles["Normal"]))
        elementos.append(Paragraph(f"<b>Descripción:</b> {reunion.descripcion or ''}", styles["Normal"]))
        elementos.append(Spacer(1, 12))

        # Intervenciones y comentarios
        elementos.append(Paragraph("<b>Intervenciones y Comentarios</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 6))

        for intervencion in reunion.intervenciones.all():
            # Intervención con autor en rojo
            contenido_intervencion = f'<font color="red">{intervencion.autor.get_full_name()}</font>: {intervencion.contenido}'
            elementos.append(Paragraph(contenido_intervencion, estilo_intervencion))

            # Comentarios de la intervención con autor en rojo
            for comentario in intervencion.comentarios.all():
                contenido_comentario = f'<font color="green">{comentario.autor.get_full_name()}</font>: {comentario.contenido}'
                elementos.append(Paragraph(contenido_comentario, estilo_comentario))

            elementos.append(Spacer(1, 6))

        # Generar PDF
        doc.build(elementos, onFirstPage=header_footer, onLaterPages=header_footer)
        return response

class DocumentosView(TemplateView):
    template_name = 'mi_aplicacion/documentos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aquí puedes pasar listas de documentos, filtradas por tipo
        context['actas'] = []         # Lista de actas
        context['compromisos'] = []   # Lista de compromisos
        context['acuerdos'] = []      # Lista de acuerdos
        return context

class ActasPorProyectoView(ListView):
    model = Reunion
    template_name = "mi_aplicacion/actas.html"
    context_object_name = "reuniones"

    def get_queryset(self):
        queryset = super().get_queryset()
        proyecto_id = self.request.GET.get("proyecto")
        if proyecto_id:
            queryset = queryset.filter(proyecto_id=proyecto_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["proyectos"] = Proyecto.objects.all()
        context["proyecto_seleccionado"] = self.request.GET.get("proyecto")
        return context
    
class HomeView(TemplateView):
    template_name = 'mi_aplicacion/home.html'

class ExportarProyectoPDF(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            proyecto = Proyecto.objects.get(pk=pk)
        except Proyecto.DoesNotExist:
            raise Http404("El proyecto no existe")

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Proyecto_{proyecto.nombre}.pdf"'

        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=5 * cm,
            bottomMargin=3 * cm
        )
        styles = getSampleStyleSheet()
        elementos = []

        # Estilos personalizados
        estilo_titulo = ParagraphStyle(
            name="Titulo",
            fontSize=14,
            leading=16,
            spaceAfter=12,
            alignment=TA_JUSTIFY
        )

        estilo_subtitulo = ParagraphStyle(
            name="Subtitulo",
            fontSize=12,
            leading=14,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName="Helvetica-Bold"
        )

        estilo_texto = ParagraphStyle(
            name="Texto",
            fontSize=10,
            leading=12,
            spaceAfter=4,
            alignment=TA_JUSTIFY
        )

        estilo_intervencion = ParagraphStyle(
            name="Intervencion",
            fontSize=10,
            leading=14,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )

        estilo_comentario = ParagraphStyle(
            name="Comentario",
            fontSize=10,
            leading=12,
            leftIndent=1*cm,
            spaceAfter=4,
            alignment=TA_JUSTIFY,
            fontName="Helvetica-Oblique"
        )

        # Header y Footer
        def header_footer(canvas, doc):
            banner_path = finders.find('img/banner.png')
            if banner_path:
                canvas.drawImage(banner_path, x=0, y=A4[1] - 4 * cm, width=A4[0], height=3 * cm)
            footer_path = finders.find('img/footer.png')
            if footer_path:
                canvas.drawImage(footer_path, x=0, y=0, width=A4[0], height=2 * cm)

        # Título del proyecto
        elementos.append(Paragraph(f"<b>Proyecto:</b> {proyecto.nombre}", estilo_titulo))
        elementos.append(Spacer(1, 12))

        # Iterar reuniones
        for reunion in proyecto.reuniones.all():
            elementos.append(Paragraph(f"Reunión: {reunion.titulo} ({reunion.fecha.strftime('%d/%m/%Y')})", estilo_subtitulo))
            elementos.append(Paragraph(f"<b>Fecha:</b> {reunion.fecha.strftime('%d/%m/%Y')}", styles["Normal"]))
            elementos.append(Paragraph(f"<b>Proyecto:</b> {reunion.proyecto.nombre if reunion.proyecto else ''}", styles["Normal"]))
            elementos.append(Paragraph(f"<b>Frente:</b> {reunion.frente.nombre if reunion.frente else ''}", styles["Normal"]))
            elementos.append(Paragraph(f"<b>Estado:</b> {reunion.estado}", styles["Normal"]))
            elementos.append(Paragraph(f"<b>Descripción:</b> {reunion.descripcion or ''}", styles["Normal"]))
            elementos.append(Spacer(1, 12))

             # Intervenciones y comentarios
            elementos.append(Paragraph("<b>Intervenciones y Comentarios</b>", styles["Heading2"]))
            elementos.append(Spacer(1, 6))

            for intervencion in reunion.intervenciones.all():
            # Intervención con autor en rojo
                contenido_intervencion = f'<font color="red">{intervencion.autor.get_full_name()}</font>: {intervencion.contenido}'
                elementos.append(Paragraph(contenido_intervencion, estilo_intervencion))

                # Comentarios de la intervención con autor en rojo
                for comentario in intervencion.comentarios.all():
                    contenido_comentario = f'<font color="green">{comentario.autor.get_full_name()}</font>: {comentario.contenido}'
                    elementos.append(Paragraph(contenido_comentario, estilo_comentario))

                elementos.append(Spacer(1, 6))

        # Construir el PDF
        doc.build(elementos, onFirstPage=header_footer, onLaterPages=header_footer)

        return response
    
class GraficoReunionesView(TemplateView):
    template_name = "mi_aplicacion/grafico_reuniones.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Capturar filtros
        estado = self.request.GET.get("estado")
        proyecto = self.request.GET.get("proyecto")
        frente = self.request.GET.get("frente")

        # Query base (aplicar filtros si vienen)
        reuniones = Reunion.objects.all()

        if estado:
            reuniones = reuniones.filter(estado=estado)
        if proyecto:
            reuniones = reuniones.filter(proyecto_id=proyecto)
        if frente:
            reuniones = reuniones.filter(frente_id=frente)

        # Datos por estado (para los gráficos que ya tenías)
        datos_estado = reuniones.values("estado").annotate(cantidad=Count("id")).order_by("estado")
        estados = [d["estado"] for d in datos_estado]
        cantidades = [d["cantidad"] for d in datos_estado]

        # --- Nuevo: calcular vencidas / activas / sin fecha (para el proyecto o filtros aplicados) ---
        today = timezone.localdate()
        vencidas = 0
        activas = 0
        sin_fecha = 0

        # Recorremos reuniones filtradas y clasificamos según fecha_finalizacion
        for r in reuniones:
            if r.fecha_finalizacion:
                # `fecha_finalizacion` es DateTimeField; comparamos por fecha (date)
                try:
                    final_date = r.fecha_finalizacion.date()
                except Exception:
                    # por si fuera ya date
                    final_date = r.fecha_finalizacion
                if final_date < today:
                    vencidas += 1
                else:
                    activas += 1
            else:
                sin_fecha += 1

        vencido_labels = ["Activas", "Vencidas", "Sin fecha"]
        vencido_counts = [activas, vencidas, sin_fecha]

        # Pasar datos al template
        context["estados"] = estados
        context["cantidades"] = cantidades

        context["vencido_labels"] = vencido_labels
        context["vencido_counts"] = vencido_counts

        # Para los selects del formulario
        context["proyectos"] = Proyecto.objects.order_by("nombre")
        context["frentes"] = Frente.objects.order_by("nombre")
        context["estado_seleccionado"] = estado or ""
        context["proyecto_seleccionado"] = proyecto or ""
        context["frente_seleccionado"] = frente or ""

        return context


# class ProyectoListView(LoginRequiredMixin, ListView):
#     model = Proyecto
#     template_name = "mi_aplicacion/proyecto_list.html"
#     context_object_name = "proyectos"
#     # paginate_by = 10

#     def get_queryset(self):
#         qs = Proyecto.objects.all().order_by("nombre")
#         return qs

class ProyectoListView(LoginRequiredMixin, ListView):
    model = Proyecto
    template_name = "mi_aplicacion/proyecto_list.html"
    context_object_name = "proyectos"

    def get_queryset(self):
        qs = Proyecto.objects.all().order_by("nombre")
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(nombre__icontains=query) | Q(descripcion__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "") 
        return context 
    
# Ver detalle de un proyecto
class ProyectoDetailView(DetailView):
    model = Proyecto
    template_name = 'mi_aplicacion/proyecto_detail.html'
    context_object_name = 'proyecto'

# Crear proyecto
class ProyectoCreateView(CreateView):
    model = Proyecto
    template_name = 'mi_aplicacion/proyecto_form.html'
    fields = ['nombre', 'descripcion', 'fecha_inicio', 'fecha_fin']
    success_url = reverse_lazy('proyecto_list')

# Editar proyecto
class ProyectoUpdateView(UpdateView):
    model = Proyecto
    template_name = 'mi_aplicacion/proyecto_form.html'
    fields = ['nombre', 'descripcion', 'fecha_inicio', 'fecha_fin']
    success_url = reverse_lazy('proyecto_list')

# Eliminar proyecto
class ProyectoDeleteView(DeleteView):
    model = Proyecto
    template_name = 'mi_aplicacion/proyecto_confirm_delete.html'
    success_url = reverse_lazy('proyecto_list')

