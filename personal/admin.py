from django.contrib import admin,messages
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.utils import timezone
from .models import Area,Empleado,Asistencia,Permiso,Correccion,Auditoria,Notificacion
from .services import rrhh,jefe,perfil,autoriza_decision,decidir_permiso,auditar

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display=['nombre'];search_fields=['nombre']
    def has_module_permission(self,request):return rrhh(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user)
    def has_change_permission(self,request,obj=None):return rrhh(request.user)
    def has_add_permission(self,request):return rrhh(request.user)
    def has_delete_permission(self,request,obj=None):return rrhh(request.user)

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display=['dni','nombres','apellidos','cargo','area','rol','antiguedad_col','vacaciones_col']
    list_filter=['area','rol','tipo_contrato'];search_fields=['dni','nombres','apellidos','email']
    list_select_related=['area','usuario']
    readonly_fields=['antiguedad_col','vacaciones_col']
    def antiguedad_col(self,obj):return obj.antiguedad
    antiguedad_col.short_description='Antigüedad'
    def vacaciones_col(self,obj):return obj.vacaciones_disponibles
    vacaciones_col.short_description='Vacaciones restantes'
    def has_module_permission(self,request):return rrhh(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user)
    def has_change_permission(self,request,obj=None):return rrhh(request.user)
    def has_add_permission(self,request):return rrhh(request.user)
    def has_delete_permission(self,request,obj=None):return rrhh(request.user)
    def save_model(self,request,obj,form,change):
        obj.full_clean();super().save_model(request,obj,form,change);auditar(request,'empleado_actualizado' if change else 'empleado_creado',obj.pk)

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display=['empleado','fecha','entrada','salida','horas_col','extras_col','area_col']
    list_filter=['fecha','empleado__area'];search_fields=['empleado__dni','empleado__nombres','empleado__apellidos']
    list_select_related=['empleado__area'];readonly_fields=['horas_col','extras_col']
    def horas_col(self,obj):return obj.horas
    horas_col.short_description='Horas trabajadas'
    def extras_col(self,obj):return obj.extras
    extras_col.short_description='Horas extras'
    def area_col(self,obj):return obj.empleado.area
    area_col.short_description='Área'
    def get_queryset(self,request):
        qs=super().get_queryset(request)
        if jefe(request.user) and not rrhh(request.user):return qs.filter(empleado__area=perfil(request.user).area)
        return qs
    def has_module_permission(self,request):return rrhh(request.user) or jefe(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user) or (jefe(request.user) and (obj is None or obj.empleado.area_id==perfil(request.user).area_id))
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False # correcciones solo por vista auditada
    def has_delete_permission(self,request,obj=None):return False

@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display=['empleado','tipo','fecha_inicio','fecha_fin','estado','area_col','saldo_col']
    list_filter=['estado','tipo','fecha_inicio','empleado__area'];search_fields=['empleado__dni','empleado__nombres','empleado__apellidos']
    list_select_related=['empleado__area'];actions=['aprobar_seleccionados']
    readonly_fields=['decidido_por','decidido_en','creado']
    def area_col(self,obj):return obj.empleado.area
    area_col.short_description='Área'
    def saldo_col(self,obj):return obj.empleado.vacaciones_disponibles
    saldo_col.short_description='Saldo vacaciones'
    def get_queryset(self,request):
        qs=super().get_queryset(request)
        if jefe(request.user) and not rrhh(request.user):return qs.filter(empleado__area=perfil(request.user).area)
        return qs
    def has_module_permission(self,request):return rrhh(request.user) or jefe(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user) or (jefe(request.user) and (obj is None or obj.empleado.area_id==perfil(request.user).area_id))
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False
    @admin.action(description='Aprobar permisos seleccionados')
    def aprobar_seleccionados(self,request,queryset):
        n=0
        for p in queryset:
            if not autoriza_decision(request.user,p) or p.estado!='pendiente':continue
            try:decidir_permiso(request,p.pk,'aprobado');n+=1
            except ValidationError as e:self.message_user(request,f'Permiso {p.pk}: {"; ".join(e.messages)}',level=messages.ERROR)
        self.message_user(request,f'Se aprobaron {n} permisos.')

@admin.register(Correccion)
class CorreccionAdmin(admin.ModelAdmin):
    list_display=['asistencia','autor','motivo','creado'];list_filter=['motivo','creado'];readonly_fields=[f.name for f in Correccion._meta.fields]
    def has_module_permission(self,request):return rrhh(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user)
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False

@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display=['momento','actor','accion','objeto','ip'];list_filter=['accion','momento'];search_fields=['accion','objeto','actor__username'];readonly_fields=[f.name for f in Auditoria._meta.fields]
    def has_module_permission(self,request):return rrhh(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user)
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display=['empleado','mensaje','creado','leida'];list_filter=['leida'];readonly_fields=[f.name for f in Notificacion._meta.fields]
    def has_module_permission(self,request):return rrhh(request.user)
    def has_view_permission(self,request,obj=None):return rrhh(request.user)
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False
