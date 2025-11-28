from django import forms
from .models import Orden
from django.contrib.auth.models import User
from .models import Perfil

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

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Apellido'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}),
        }

class PerfilUpdateForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['telefono', 'direccion', 'ciudad', 'codigo_postal', 'foto']
        widgets = {
            'telefono': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Teléfono'}),
            'direccion': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Dirección de envío'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ciudad'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'CP'}),
            # La foto no lleva widget especial, Django la maneja
        }