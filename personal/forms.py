from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Permiso,Asistencia,Empleado,sanitize_text

class StyledFormMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():field.widget.attrs.setdefault('class','control')

class PermisoForm(StyledFormMixin,forms.ModelForm):
    class Meta:
        model=Permiso
        fields=['tipo','fecha_inicio','fecha_fin','motivo','adjunto_descripcion']
        widgets={'fecha_inicio':forms.DateInput(attrs={'type':'date'}),'fecha_fin':forms.DateInput(attrs={'type':'date'}),'motivo':forms.Textarea(attrs={'rows':4,'placeholder':'Explique el motivo (30 caracteres como mínimo)'})}
    def clean_motivo(self):
        value=sanitize_text(self.cleaned_data['motivo'])
        if len(value)<30:raise ValidationError('Escriba al menos 30 caracteres.')
        return value
    def clean_adjunto_descripcion(self):return sanitize_text(self.cleaned_data.get('adjunto_descripcion',''))
    def clean(self):
        result=super().clean()
        if result.get('fecha_inicio') and result.get('fecha_fin') and result['fecha_fin']<result['fecha_inicio']:self.add_error('fecha_fin','La fecha final debe ser igual o posterior al inicio.')
        return result

class CorreccionForm(StyledFormMixin,forms.Form):
    motivo=forms.ChoiceField(choices=[('sistema','Error de sistema'),('olvido','Olvido'),('otro','Otro')])
    justificacion=forms.CharField(widget=forms.Textarea(attrs={'rows':4}),min_length=50)
    entrada=forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(date_attrs={'type':'date'},time_attrs={'type':'time'}))
    salida=forms.SplitDateTimeField(required=False,widget=forms.SplitDateTimeWidget(date_attrs={'type':'date'},time_attrs={'type':'time'}))
    def clean_justificacion(self):
        value=sanitize_text(self.cleaned_data['justificacion'])
        if len(value)<50:raise ValidationError('Se requieren 50 caracteres como mínimo.')
        return value
    def clean(self):
        data=super().clean()
        if data.get('entrada') and data.get('salida') and data['salida']<=data['entrada']:self.add_error('salida','La salida debe ser posterior a la entrada.')
        return data

class EmpleadoForm(StyledFormMixin,forms.ModelForm):
    class Meta:
        model=Empleado
        fields=['dni','nombres','apellidos','cargo','area','fecha_ingreso','tipo_contrato','email','rol','salario']
        widgets={'fecha_ingreso':forms.DateInput(attrs={'type':'date'})}
