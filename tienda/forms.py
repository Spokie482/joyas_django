from django import forms
from .models import Orden

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Orden
        fields = ['direccion', 'ciudad', 'codigo_postal', 'telefono']
        # Estilos para que se vean bien (clases CSS)
        widgets = {
            'direccion': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Calle y número'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Tu ciudad'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'CP'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Teléfono de contacto'}),
        }