# mi_aplicacion/forms.py

from django import forms
from .models import Intervencion, Comentario, IntervencionDocumento, Reunion, Proyecto, Frente

class IntervencionForm(forms.ModelForm):
    class Meta:
        model = Intervencion
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe tu intervención...'}),
        }

class IntervencionDocumentoForm(forms.ModelForm):
    class Meta:
        model = IntervencionDocumento
        fields = ['archivo', 'nombre']
        widgets = {
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre opcional'}),
        }

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '💬 Escribe tu comentario...',
                'class': 'form-control rounded-3 shadow-sm border-light focus-ring focus-ring-primary'
            })
        }

class ReunionForm(forms.ModelForm):
    class Meta:
        model = Reunion
        fields = [
            'proyecto',
            'frente',
            'titulo',
            'descripcion',
            'estado',
            'grupo_trabajo',
            'etiquetas',
            'documentos',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'grupo_trabajo': forms.Select(attrs={'class': 'form-select'}),
            'etiquetas': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        proyecto = kwargs.pop('proyecto', None)
        super().__init__(*args, **kwargs)

        if self.instance and getattr(self.instance, 'proyecto', None):
            proyecto = self.instance.proyecto

        if proyecto:
            try:
                proyecto_id = proyecto.pk if hasattr(proyecto, 'pk') else int(proyecto)
                self.fields['frente'].queryset = Frente.objects.filter(proyecto_id=proyecto_id).order_by('nombre')
                self.fields['frente'].disabled = False
            except Exception:
                self.fields['frente'].queryset = Frente.objects.none()
        else:
            self.fields['frente'].queryset = Frente.objects.none()
            self.fields['frente'].disabled = True

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField(label="Seleccionar archivo CSV")

class ReunionForm(forms.ModelForm):
    class Meta:
        model = Reunion
        fields = "__all__"
        widgets = {
            "fecha": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "fecha_finalizacion": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }