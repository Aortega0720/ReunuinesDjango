# mi_aplicacion/forms.py

from django import forms
from .models import Intervencion, Comentario, IntervencionDocumento

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
