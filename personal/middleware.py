import logging
from datetime import time
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.utils import timezone
from .services import perfil,auditar
from .models import Asistencia
log=logging.getLogger('personal.audit')
class AccountBlockMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated and not request.user.is_active:
            log.warning('Acceso bloqueado: cuenta desactivada %s',request.user.pk)
            return HttpResponseForbidden('Cuenta desactivada.')
        return self.get_response(request)
class AttendanceReminderMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated and request.path=='/':
            e=perfil(request.user)
            if e and e.rol!='contador' and timezone.localdate().weekday()<5 and not Asistencia.objects.filter(empleado=e,fecha=timezone.localdate()).exists():
                messages.warning(request,'Recordatorio: todavía no ha marcado su entrada de hoy.')
        return self.get_response(request)
class AttendanceWindowMiddleware:
    """Controla solicitudes POST a marcación. Horario de laboratorio: 08:00 a 17:00, tolerancia de 2h.
    Entrada 06:00-10:00; salida 15:00-19:00. Admite marcar salida en hora de entrada+2h
    si se requiere turno corto, evitando bloquear la práctica (ventana global 06-19).
    """
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.path=='/asistencia/marcar/' and request.method=='POST':
            local=timezone.localtime();h=local.time()
            if local.weekday()>=5 or not time(6)<=h<=time(19):
                log.warning('Marcación fuera de horario usuario=%s ip=%s',request.user,request.META.get('REMOTE_ADDR'))
                return HttpResponseForbidden('Marcación permitida de lunes a viernes entre 06:00 y 19:00 (horario referencial 08:00–17:00 ±2h).')
        return self.get_response(request)
class AuditRequestMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if request.method=='POST' and request.path.startswith(('/asistencia/','/permisos/')):
            log.info('POST usuario=%s ruta=%s status=%s ip=%s',request.user,request.path,response.status_code,request.META.get('REMOTE_ADDR'))
        if response.status_code in (401,403):log.warning('ACCESO DENEGADO usuario=%s ruta=%s ip=%s',request.user,request.path,request.META.get('REMOTE_ADDR'))
        return response
