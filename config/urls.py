from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views
urlpatterns=[path('admin/',admin.site.urls),path('cuentas/ingresar/',auth_views.LoginView.as_view(template_name='registration/login.html'),name='login'),path('cuentas/salir/',auth_views.LogoutView.as_view(),name='logout'),path('',include('personal.urls'))]
admin.site.site_header='TecnoAndes | Recursos Humanos'
admin.site.site_title='Gestión RRHH'
admin.site.index_title='Operaciones y auditoría'
