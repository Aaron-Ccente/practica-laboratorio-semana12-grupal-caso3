from django.apps import AppConfig
class PersonalConfig(AppConfig):
    default_auto_field='django.db.models.BigAutoField'
    name='personal'
    verbose_name='Control de asistencia y permisos'
    def ready(self):
        import personal.signals  # noqa
