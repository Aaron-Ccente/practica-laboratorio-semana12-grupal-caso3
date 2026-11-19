from datetime import timedelta,datetime,time
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Area,Empleado,Permiso,Asistencia

class ReglasNegocioTests(TestCase):
    def setUp(self):
        self.area=Area.objects.create(nombre='Sistemas')
        self.user=User.objects.create_user('empleado',password='Prueba123!')
        self.jefe_user=User.objects.create_user('jefe',password='Prueba123!')
        hoy=timezone.localdate()
        self.emp=Empleado.objects.create(usuario=self.user,dni='12345678',nombres='Test',apellidos='Empleado',cargo='Analista',area=self.area,fecha_ingreso=hoy-timedelta(days=30),tipo_contrato='planilla',email='empleado@tecnoandes.pe')
        self.jefe=Empleado.objects.create(usuario=self.jefe_user,dni='87654321',nombres='Test',apellidos='Jefe',cargo='Supervisor',area=self.area,fecha_ingreso=hoy-timedelta(days=90),tipo_contrato='planilla',email='jefe@tecnoandes.pe',rol='jefe')
    def nuevo_permiso(self,inicio=None,fin=None,motivo='Solicitud de permiso personal suficientemente detallada para la revisión.'):
        inicio=inicio or timezone.localdate()+timedelta(days=10)
        return Permiso(empleado=self.emp,tipo='personal',fecha_inicio=inicio,fecha_fin=fin or inicio,motivo=motivo)
    def test_correo_institucional(self):
        self.emp.email='correo@gmail.com'
        with self.assertRaises(ValidationError):self.emp.full_clean()
    def test_fecha_ingreso_futura(self):
        self.emp.fecha_ingreso=timezone.localdate()+timedelta(days=1)
        with self.assertRaises(ValidationError):self.emp.full_clean()
    def test_permiso_fecha_invalida(self):
        p=self.nuevo_permiso();p.fecha_fin=p.fecha_inicio-timedelta(days=1)
        with self.assertRaises(ValidationError):p.full_clean()
    def test_permiso_superpuesto(self):
        p=self.nuevo_permiso();p.full_clean();p.save()
        with self.assertRaises(ValidationError):self.nuevo_permiso().full_clean()
    def test_saldo_vacaciones(self):
        p=self.nuevo_permiso();p.tipo='vacaciones';p.fecha_fin=p.fecha_inicio+timedelta(days=30)
        with self.assertRaises(ValidationError):p.full_clean()
    def test_empleado_no_accede_a_reportes(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('reportes')).status_code,403)
    def test_jefe_puede_aprobar_misma_area(self):
        p=self.nuevo_permiso();p.full_clean();p.save()
        self.client.force_login(self.jefe_user)
        response=self.client.post(reverse('decidir_permiso',args=[p.pk,'aprobado']))
        p.refresh_from_db();self.assertEqual(p.estado,'aprobado');self.assertEqual(response.status_code,302)
    def test_empleado_no_puede_aprobar(self):
        p=self.nuevo_permiso();p.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('decidir_permiso',args=[p.pk,'aprobado'])).status_code,403)
    def test_doble_asistencia_prohibida(self):
        ahora=timezone.now();hoy=timezone.localdate()
        Asistencia.objects.create(empleado=self.emp,fecha=hoy,entrada=ahora)
        with self.assertRaises(ValidationError):
            a=Asistencia(empleado=self.emp,fecha=hoy,entrada=ahora);a.full_clean()
    def test_salida_antes_de_entrada(self):
        ahora=timezone.now();a=Asistencia(empleado=self.emp,fecha=timezone.localdate(),entrada=ahora,salida=ahora-timedelta(hours=1))
        with self.assertRaises(ValidationError):a.full_clean()
    def test_timeout_45_minutos(self):
        from django.conf import settings
        self.assertEqual(settings.SESSION_COOKIE_AGE,2700)
