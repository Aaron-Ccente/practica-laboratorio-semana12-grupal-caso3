"""Datos DEMOSTRATIVOS ficticios e idempotentes, nunca usar en producción."""
from datetime import timedelta,datetime,time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User,Group,Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from personal.models import Area,Empleado,Asistencia,Permiso
class Command(BaseCommand):
    help='Prepara 5 áreas, 12 empleados, 60 asistencias y 12 permisos ficticios.'
    def handle(self,*args,**options):
        areas={n:Area.objects.get_or_create(nombre=n)[0] for n in ['Sistemas','Contabilidad','Ventas','Logística','RRHH']}
        roles={'rrhh':'Admins RRHH','jefe':'Jefes de Área','empleado':'Empleados','contador':'Contadores'}
        groups={k:Group.objects.get_or_create(name=v)[0] for k,v in roles.items()}
        cts={m:ContentType.objects.get_for_model(m) for m in (Asistencia,Permiso)}
        perms=[('registrar_asistencia',cts[Asistencia]),('corregir_asistencia',cts[Asistencia]),('solicitar_permiso',cts[Permiso]),('aprobar_permiso',cts[Permiso])]
        for cod,ct in perms:Permission.objects.get_or_create(content_type=ct,codename=cod,defaults={'name':cod.replace('_',' ').title()})
        for k,g in groups.items():
            selected={'rrhh':['registrar_asistencia','solicitar_permiso','aprobar_permiso','corregir_asistencia'],'jefe':['registrar_asistencia','solicitar_permiso','aprobar_permiso'],'empleado':['registrar_asistencia','solicitar_permiso'],'contador':[]}[k]
            g.permissions.set([Permission.objects.get(content_type=ct,codename=cod) for cod,ct in perms if cod in selected])
        empleados=[]
        specs=[('rrhh','Admin','Recursos','RRHH','rrhh'),('jefe_sistemas','Laura','Quispe','Sistemas','jefe'),('jefe_ventas','Marco','Rojas','Ventas','jefe'),('jefe_logistica','Ana','Huaman','Logística','jefe'),('empleado1','Pedro','Soto','Sistemas','empleado'),('empleado2','Maria','Condori','Sistemas','empleado'),('empleado3','José','Paredes','Ventas','empleado'),('empleado4','Lucia','Vega','Ventas','empleado'),('empleado5','Carla','Ramos','Logística','empleado'),('empleado6','Diego','Torres','Contabilidad','empleado'),('empleado7','Miriam','Palacios','Contabilidad','empleado'),('contador','Elena','Castro','Contabilidad','contador')]
        hoy=timezone.localdate()
        for i,(username,nombres,apellidos,area,rol) in enumerate(specs):
            user,created=User.objects.get_or_create(username=username,defaults={'first_name':nombres,'last_name':apellidos,'email':f'{username}@tecnoandes.pe','is_staff':rol in ('rrhh','jefe')})
            if created:user.set_password('Demo2026!Segura');user.save()
            user.groups.set([groups[rol]])
            emp,_=Empleado.objects.get_or_create(usuario=user,defaults={'dni':f'{70000000+i}','nombres':nombres,'apellidos':apellidos,'cargo':{'rrhh':'Gerente de RRHH','jefe':'Supervisor','empleado':'Analista','contador':'Analista de planillas'}[rol],'area':areas[area],'fecha_ingreso':hoy-timedelta(days=500+i*30),'tipo_contrato':'planilla','email':f'{username}@tecnoandes.pe','rol':rol,'salario':2200+i*140})
            empleados.append(emp)
        # cinco días pasados por 12 empleados = 60 marcaciones de jornada completa
        dia=hoy-timedelta(days=1);fechas=[]
        while len(fechas)<5:
            if dia.weekday()<5:fechas.append(dia)
            dia-=timedelta(days=1)
        for idx,e in enumerate(empleados):
            for j,d in enumerate(fechas):
                entrada=timezone.make_aware(datetime.combine(d,time(8,0)))
                salida=entrada+timedelta(hours=8+(1 if (idx+j)%3==0 else 0))
                Asistencia.objects.get_or_create(empleado=e,fecha=d,defaults={'entrada':entrada,'salida':salida})
        # 12 permisos futuros sin solapamientos por empleado
        for i,e in enumerate(empleados):
            inicio=hoy+timedelta(days=20+i*3)
            p,_=Permiso.objects.get_or_create(empleado=e,fecha_inicio=inicio,defaults={'fecha_fin':inicio+timedelta(days=1),'tipo':'vacaciones' if i%3==0 else 'personal','motivo':'Solicitud ficticia para la demostración de validaciones del sistema de RRHH.','adjunto_descripcion':'Documento demostrativo no adjuntado'})
        self.stdout.write(self.style.SUCCESS(f'Demo preparada: {Empleado.objects.count()} empleados, {Area.objects.count()} áreas, {Asistencia.objects.count()} asistencias, {Permiso.objects.count()} permisos.'))
        self.stdout.write('Cuentas nuevas: rrhh, jefe_sistemas, empleado1, contador | contraseña inicial: Demo2026!Segura (CAMBIAR).')
