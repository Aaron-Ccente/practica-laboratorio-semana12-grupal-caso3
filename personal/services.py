import logging
from datetime import timedelta
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction,IntegrityError
from django.utils import timezone
from .models import Asistencia,Auditoria,Notificacion,Permiso
log=logging.getLogger('personal.audit')

def perfil(user):
    try:return user.perfil
    except Exception:return None

def rrhh(user):return user.is_authenticated and (user.is_superuser or (perfil(user) and perfil(user).rol=='rrhh'))
def jefe(user):return user.is_authenticated and perfil(user) and perfil(user).rol=='jefe'
def reporte_global(user):return rrhh(user) or (perfil(user) and perfil(user).rol=='contador')
def ip_cliente(request):return request.META.get('REMOTE_ADDR')

def auditar(request,accion,objeto,detalle=''):
    actor=request.user if request.user.is_authenticated else None
    Auditoria.objects.create(actor=actor,accion=accion,objeto=str(objeto)[:180],detalle=str(detalle)[:2000],ip=ip_cliente(request))
    log.info('actor=%s ip=%s accion=%s objeto=%s detalle=%s',actor,ip_cliente(request),accion,objeto,detalle)

def autoriza_decision(user,permiso):
    return rrhh(user) or (jefe(user) and permiso.empleado.area_id==perfil(user).area_id and permiso.empleado_id!=perfil(user).id)

@transaction.atomic
def decidir_permiso(request,pk,decision):
    p=Permiso.objects.select_for_update().select_related('empleado__area').get(pk=pk)
    if not autoriza_decision(request.user,p):raise PermissionDenied('No puede resolver solicitudes ajenas a su área.')
    if p.estado!='pendiente':raise ValidationError('Solo se pueden resolver permisos pendientes.')
    if decision not in ['aprobado','rechazado']:raise ValidationError('Decisión inválida.')
    p.estado=decision
    p.full_clean()
    p.decidido_por=request.user;p.decidido_en=timezone.now();p.save(update_fields=['estado','decidido_por','decidido_en'])
    Notificacion.objects.create(empleado=p.empleado,mensaje=f'Su solicitud {p.get_tipo_display()} del {p.fecha_inicio} al {p.fecha_fin} fue {decision}.')
    auditar(request,'permiso_'+decision,p.pk, f'empleado={p.empleado_id}')
    return p

@transaction.atomic
def marcar(request):
    empleado=perfil(request.user)
    if not empleado or empleado.rol=='contador':raise PermissionDenied('No tiene habilitada la marcación.')
    ahora=timezone.now();hoy=timezone.localdate()
    a=Asistencia.objects.select_for_update().filter(empleado=empleado,fecha=hoy).first()
    if not a:
        try:
            a=Asistencia(empleado=empleado,fecha=hoy,entrada=ahora);a.full_clean();a.save()
        except IntegrityError:raise ValidationError('Ya existe una marcación de entrada para hoy.')
        auditar(request,'entrada',a.pk, f'{empleado} {ahora.isoformat()}')
        return 'Entrada registrada.'
    if a.salida:raise ValidationError('Ya registró entrada y salida hoy.')
    if ahora<=a.entrada:raise ValidationError('La salida debe ser posterior a la entrada.')
    a.salida=ahora;a.full_clean();a.save(update_fields=['salida','ultima_modificacion'])
    auditar(request,'salida',a.pk, f'{empleado} horas={a.horas} extras={a.extras}')
    return 'Salida registrada.'
