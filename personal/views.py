from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Sum,Count
from django.http import HttpResponse,HttpResponseForbidden
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from .forms import PermisoForm,CorreccionForm
from .models import Asistencia,Permiso,Empleado,Correccion,Notificacion,Auditoria
from .services import perfil,rrhh,jefe,reporte_global,autoriza_decision,decidir_permiso,marcar,auditar

def role_required(*roles):
    def deco(view):
        from functools import wraps
        @login_required
        @wraps(view)
        def wrapper(request,*args,**kwargs):
            if not (rrhh(request.user) and 'rrhh' in roles) and not (perfil(request.user) and perfil(request.user).rol in roles):raise PermissionDenied('Su rol no tiene acceso a esta función.')
            return view(request,*args,**kwargs)
        return wrapper
    return deco

@login_required
def inicio(request):
    e=perfil(request.user)
    if not e and not request.user.is_superuser:raise PermissionDenied('No existe un perfil asociado.')
    asistencias=Asistencia.objects.select_related('empleado').filter(empleado=e)[:8] if e else []
    permisos=Permiso.objects.select_related('empleado').filter(empleado=e)[:6] if e else []
    avisos=Notificacion.objects.filter(empleado=e,leida=False)[:5] if e else []
    return render(request,'personal/inicio.html',{'empleado':e,'asistencias':asistencias,'permisos':permisos,'avisos':avisos,'es_rrhh':rrhh(request.user),'es_jefe':jefe(request.user),'puede_reporte':reporte_global(request.user) or jefe(request.user)})

@role_required('rrhh','jefe','empleado')
def marcar_asistencia(request):
    if request.method!='POST':return redirect('inicio')
    try:messages.success(request,marcar(request))
    except ValidationError as e:messages.error(request,'; '.join(e.messages))
    return redirect('inicio')

@role_required('rrhh','jefe','empleado')
def solicitar_permiso(request):
    e=perfil(request.user)
    if not e:raise PermissionDenied('Perfil obligatorio.')
    form=PermisoForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        p=form.save(commit=False);p.empleado=e;p.estado='pendiente'
        try:
            with transaction.atomic():p.full_clean();p.save();auditar(request,'permiso_creado',p.pk,f'tipo={p.tipo}')
        except ValidationError as err:
            for error in err.messages:form.add_error(None,error)
        else:
            messages.success(request,'Solicitud registrada. Está pendiente de aprobación.')
            return redirect('mis_permisos')
    return render(request,'personal/formulario.html',{'form':form,'titulo':'Nueva solicitud de permiso o vacaciones','boton':'Enviar solicitud'})

@login_required
def mis_permisos(request):
    e=perfil(request.user)
    if not e:return render(request,'personal/lista_permisos.html',{'permisos':[],'titulo':'Mis solicitudes'})
    return render(request,'personal/lista_permisos.html',{'permisos':Permiso.objects.filter(empleado=e).select_related('empleado','decidido_por'),'titulo':'Mis solicitudes'})

@role_required('rrhh','jefe')
def revisar_permisos(request):
    qs=Permiso.objects.select_related('empleado','empleado__area','decidido_por')
    if not rrhh(request.user):qs=qs.filter(empleado__area=perfil(request.user).area).exclude(empleado=perfil(request.user))
    return render(request,'personal/lista_permisos.html',{'permisos':qs,'titulo':'Solicitudes de mi ámbito','revisar':True})

@role_required('rrhh','jefe')
def decidir(request,pk,decision):
    if request.method!='POST':return HttpResponse(status=405)
    try:
        p=decidir_permiso(request,pk,decision)
        messages.success(request,f'Solicitud {p.get_estado_display().lower()}.')
    except ValidationError as e:messages.error(request,'; '.join(e.messages))
    return redirect('revisar_permisos')

@login_required
def historial(request):
    e=perfil(request.user)
    qs=Asistencia.objects.filter(empleado=e).select_related('empleado') if e else Asistencia.objects.none()
    return render(request,'personal/asistencias.html',{'asistencias':qs,'titulo':'Mi historial de asistencia'})

@role_required('rrhh')
def corregir(request,pk):
    a=get_object_or_404(Asistencia.objects.select_related('empleado'),pk=pk)
    form=CorreccionForm(request.POST or None,initial={'entrada':[timezone.localtime(a.entrada).date(),timezone.localtime(a.entrada).time().replace(second=0,microsecond=0)],'salida':[timezone.localtime(a.salida).date(),timezone.localtime(a.salida).time().replace(second=0,microsecond=0)] if a.salida else None})
    if request.method=='POST' and form.is_valid():
        d=form.cleaned_data
        try:
            with transaction.atomic():
                a=Asistencia.objects.select_for_update().get(pk=pk)
                anterior=(a.entrada,a.salida)
                a.entrada=d['entrada'];a.salida=d.get('salida')
                a.full_clean();a.save()
                Correccion.objects.create(asistencia=a,autor=request.user,motivo=d['motivo'],justificacion=d['justificacion'],entrada_anterior=anterior[0],salida_anterior=anterior[1],entrada_nueva=a.entrada,salida_nueva=a.salida)
                auditar(request,'asistencia_corregida',a.pk,f'Motivo: {d["motivo"]}; antes={anterior}; después={(a.entrada,a.salida)}')
        except ValidationError as err:
            for msg in err.messages:form.add_error(None,msg)
        else:
            messages.success(request,'Corrección auditada y guardada.')
            return redirect('reportes')
    return render(request,'personal/formulario.html',{'form':form,'titulo':f'Corregir asistencia #{pk}','boton':'Guardar corrección'})

@login_required
def reportes(request):
    if not (reporte_global(request.user) or jefe(request.user)):raise PermissionDenied('Sin acceso a reportes.')
    empleados=Empleado.objects.select_related('area').all()
    asistencias=Asistencia.objects.select_related('empleado__area').all()
    permisos=Permiso.objects.select_related('empleado__area').all()
    if jefe(request.user) and not rrhh(request.user):
        area=perfil(request.user).area
        empleados=empleados.filter(area=area);asistencias=asistencias.filter(empleado__area=area);permisos=permisos.filter(empleado__area=area)
    fecha=request.GET.get('fecha')
    area_id=request.GET.get('area')
    if fecha:
        from datetime import date
        try:asistencias=asistencias.filter(fecha=date.fromisoformat(fecha))
        except ValueError:fecha=''
    if area_id and (rrhh(request.user) or (perfil(request.user) and perfil(request.user).rol=='contador')):
        asistencias=asistencias.filter(empleado__area_id=area_id);permisos=permisos.filter(empleado__area_id=area_id);empleados=empleados.filter(area_id=area_id)
    resumen=[{'empleado':x,'horas':sum((a.horas for a in x.asistencias.all()),0),'extras':sum((a.extras for a in x.asistencias.all()),0)} for x in empleados.prefetch_related('asistencias')]
    return render(request,'personal/reportes.html',{'resumen':resumen,'asistencias':asistencias[:200],'pendientes':permisos.filter(estado='pendiente').count(),'fecha':fecha,'area_id':area_id,'puede_corregir':rrhh(request.user),'puede_exportar':reporte_global(request.user)})

@login_required
def exportar(request):
    if not reporte_global(request.user):raise PermissionDenied('Solo RRHH y Contador pueden exportar.')
    from django.utils.text import slugify
    qs=Asistencia.objects.select_related('empleado__area').order_by('fecha')
    lines=['Fecha | Empleado | Área | Horas | Horas extras']
    for a in qs:lines.append(f'{a.fecha} | {a.empleado} | {a.empleado.area} | {a.horas} | {a.extras}')
    auditar(request,'reporte_exportado','asistencias','Reporte global en texto')
    response=HttpResponse('\n'.join(lines),content_type='text/plain; charset=utf-8')
    response['Content-Disposition']='attachment; filename="reporte_asistencias.txt"'
    return response

@role_required('rrhh')
def auditoria(request):
    return render(request,'personal/auditoria.html',{'logs':Auditoria.objects.select_related('actor')[:150]})
