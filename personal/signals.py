from django.contrib.auth.signals import user_logged_in,user_login_failed
from django.dispatch import receiver
from django.contrib import messages
from .models import Asistencia
from .services import perfil
import logging
from django.utils import timezone
log=logging.getLogger('personal.audit')
@receiver(user_logged_in)
def login_ok(sender,request,user,**kwargs):
    request.session.cycle_key()
    log.info('Login correcto: %s ip=%s',user,request.META.get('REMOTE_ADDR'))
@receiver(user_login_failed)
def login_fallido(sender,credentials,request,**kwargs):
    log.warning('Login fallido usuario=%s ip=%s',credentials.get('username'),request.META.get('REMOTE_ADDR') if request else '-')
