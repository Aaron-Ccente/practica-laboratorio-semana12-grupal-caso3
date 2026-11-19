from datetime import date,datetime,timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator,MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

def validate_company_email(value):
    if not value.lower().endswith('@tecnoandes.pe'):
        raise ValidationError('Utilice un correo corporativo @tecnoandes.pe.')

def sanitize_text(text):
    import re,html
    return re.sub(r'<[^>]*>','',html.unescape(text or '')).strip()

class Area(models.Model):
    nombre=models.CharField(max_length=80,unique=True)
    def __str__(self): return self.nombre
    class Meta: ordering=['nombre']; verbose_name='Área'

class Empleado(models.Model):
    ROLES=[('rrhh','Administrador RRHH'),('jefe','Jefe de área'),('empleado','Empleado'),('contador','Contador')]
    CONTRATOS=[('planilla','Planilla'),('locacion','Locación')]
    usuario=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='perfil')
    dni=models.CharField(max_length=8,unique=True,validators=[RegexValidator(r'^\d{8}$','El DNI requiere 8 dígitos.')])
    nombres=models.CharField(max_length=120)
    apellidos=models.CharField(max_length=120)
    cargo=models.CharField(max_length=120,validators=[MinLengthValidator(1)])
    area=models.ForeignKey(Area,on_delete=models.PROTECT,related_name='empleados')
    fecha_ingreso=models.DateField()
    tipo_contrato=models.CharField(max_length=10,choices=CONTRATOS)
    email=models.EmailField(unique=True,validators=[validate_company_email])
    rol=models.CharField(max_length=10,choices=ROLES,default='empleado')
    salario=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    class Meta: ordering=['apellidos','nombres']; verbose_name='Empleado'
    def __str__(self): return f'{self.nombres} {self.apellidos}'
    def clean(self):
        if self.fecha_ingreso and self.fecha_ingreso>timezone.localdate(): raise ValidationError({'fecha_ingreso':'La fecha de ingreso no puede ser futura.'})
        if not self.cargo or not self.cargo.strip(): raise ValidationError({'cargo':'El cargo es obligatorio.'})
        if self.email: validate_company_email(self.email)
    @property
    def antiguedad(self):
        today=timezone.localdate();months=(today.year-self.fecha_ingreso.year)*12+today.month-self.fecha_ingreso.month-(today.day<self.fecha_ingreso.day)
        return f'{months//12} años y {months%12} meses'
    @property
    def vacaciones_disponibles(self):
        """Saldo de práctica académica: 30 días menos permisos de vacaciones aprobados."""
        usados=sum((p.fecha_fin-p.fecha_inicio).days+1 for p in self.permisos.filter(tipo='vacaciones',estado='aprobado'))
        return max(0,30-usados)

class Asistencia(models.Model):
    empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name='asistencias')
    fecha=models.DateField(default=timezone.localdate)
    entrada=models.DateTimeField()
    salida=models.DateTimeField(blank=True,null=True)
    ultima_modificacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-fecha','-entrada']
        constraints=[models.UniqueConstraint(fields=['empleado','fecha'],name='asistencia_unica_por_dia')]
    def __str__(self): return f'{self.empleado} · {self.fecha}'
    def clean(self):
        if self.entrada and timezone.localtime(self.entrada).date()!=self.fecha: raise ValidationError({'entrada':'La entrada debe corresponder a la fecha.'})
        if self.salida and self.entrada and self.salida<=self.entrada: raise ValidationError({'salida':'La salida debe ser posterior a la entrada.'})
        if self.salida and timezone.localtime(self.salida).date()!=self.fecha: raise ValidationError({'salida':'La marcación diaria debe finalizar el mismo día.'})
    @property
    def horas(self):
        if not self.salida:return Decimal('0.00')
        return (Decimal(str((self.salida-self.entrada).total_seconds()))/Decimal('3600')).quantize(Decimal('.01'))
    @property
    def extras(self):return max(Decimal('0.00'),self.horas-Decimal('8.00'))

class Permiso(models.Model):
    TIPOS=[('personal','Personal'),('medico','Médico'),('duelo','Duelo'),('familia','Maternidad / paternidad'),('vacaciones','Vacaciones'),('otro','Otro')]
    ESTADOS=[('pendiente','Pendiente'),('aprobado','Aprobado'),('rechazado','Rechazado')]
    empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name='permisos')
    tipo=models.CharField(max_length=12,choices=TIPOS)
    fecha_inicio=models.DateField()
    fecha_fin=models.DateField()
    motivo=models.TextField(validators=[MinLengthValidator(30)])
    adjunto_descripcion=models.CharField(max_length=255,blank=True)
    estado=models.CharField(max_length=10,choices=ESTADOS,default='pendiente')
    creado=models.DateTimeField(auto_now_add=True)
    decidido_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='permisos_decididos')
    decidido_en=models.DateTimeField(null=True,blank=True)
    class Meta:ordering=['-creado']; permissions=[('aprobar_permiso','Puede aprobar permisos'),('solicitar_permiso','Puede solicitar permisos')]
    def __str__(self):return f'{self.empleado} · {self.tipo} · {self.estado}'
    def clean(self):
        self.motivo=sanitize_text(self.motivo)
        self.adjunto_descripcion=sanitize_text(self.adjunto_descripcion)
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin<self.fecha_inicio:raise ValidationError({'fecha_fin':'La fecha final no puede ser anterior a la inicial.'})
            if self.empleado_id and self.estado!='rechazado' and Permiso.objects.filter(empleado_id=self.empleado_id,estado__in=['pendiente','aprobado'],fecha_inicio__lte=self.fecha_fin,fecha_fin__gte=self.fecha_inicio).exclude(pk=self.pk).exists():raise ValidationError('Ya existe un permiso pendiente o aprobado que se superpone.')
            if self.tipo=='vacaciones' and self.empleado_id and self.estado!='rechazado':
                usados=sum((p.fecha_fin-p.fecha_inicio).days+1 for p in Permiso.objects.filter(empleado_id=self.empleado_id,tipo='vacaciones',estado='aprobado').exclude(pk=self.pk))
                if (self.fecha_fin-self.fecha_inicio).days+1>30-usados:raise ValidationError('No hay suficientes días de vacaciones disponibles.')

class Correccion(models.Model):
    MOTIVOS=[('sistema','Error de sistema'),('olvido','Olvido'),('otro','Otro')]
    asistencia=models.ForeignKey(Asistencia,on_delete=models.PROTECT,related_name='correcciones')
    autor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    motivo=models.CharField(max_length=10,choices=MOTIVOS)
    justificacion=models.TextField(validators=[MinLengthValidator(50)])
    entrada_anterior=models.DateTimeField()
    salida_anterior=models.DateTimeField(null=True,blank=True)
    entrada_nueva=models.DateTimeField()
    salida_nueva=models.DateTimeField(null=True,blank=True)
    creado=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-creado'];permissions=[('corregir_asistencia','Puede corregir asistencia')]

class Auditoria(models.Model):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    accion=models.CharField(max_length=100)
    objeto=models.CharField(max_length=180)
    detalle=models.TextField(blank=True)
    ip=models.GenericIPAddressField(null=True,blank=True)
    momento=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-momento'];verbose_name='Auditoría';verbose_name_plural='Auditorías'
    def __str__(self):return f'{self.momento} · {self.accion}'

class Notificacion(models.Model):
    empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name='notificaciones')
    mensaje=models.CharField(max_length=260)
    leida=models.BooleanField(default=False)
    creado=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-creado']
