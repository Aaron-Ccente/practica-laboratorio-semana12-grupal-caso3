# TecnoAndes S.A.C. — Caso 3, Semana 12 (IS093A)

Proyecto **Django** del **Sistema de Control de Asistencia y Permisos de Empleados** de la guía de práctica grupal de la UNCP. Solo se implementa el Caso 3.

## Requisitos
Python 3.11+ y conexión a Internet para instalar Django. Abra esta carpeta en Visual Studio Code.

## Instalación en Windows (PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations personal
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```
Visite **http://127.0.0.1:8000/**. Administración: **http://127.0.0.1:8000/admin/**.

Linux/macOS: `python3 -m venv .venv && source .venv/bin/activate`, después los mismos comandos `python ...`.

**Importante:** Las migraciones iniciales se generan con `makemigrations personal` porque la práctica se distribuye sin una base SQLite ni migraciones prefabricadas; conserve el archivo generado `personal/migrations/0001_initial.py` en su repositorio antes de enviar el proyecto. El comando `cargar_demo` es idempotente y crea datos ficticios sin sobrescribir contraseñas de usuarios existentes.

## Cuentas demostrativas

| Usuario | Rol | Contraseña inicial (demo) |
|---|---|---|
| rrhh | Administrador RRHH | Demo2026!Segura |
| jefe_sistemas | Jefe de Área | Demo2026!Segura |
| empleado1 | Empleado | Demo2026!Segura |
| contador | Contador | Demo2026!Segura |

También se crean `jefe_ventas`, `jefe_logistica` y `empleado2` a `empleado7`. **Cambie las contraseñas antes de cualquier despliegue externo.** Nunca cargue información personal real en esta demostración.

## Funcionalidades por rubro
- **RF1:** `Empleado`, `Area`, DNI único de 8 cifras, correo `@tecnoandes.pe`, cargo obligatorio, fecha de ingreso no futura, antigüedad calculada. Salarios solo en Admin para RRHH.
- **RF2:** un registro diario de asistencia por empleado, timestamp servidor, cálculo de horas y extras (>8). Corrección solo RRHH con motivo y justificación >=50 caracteres; cambio registrado en `Correccion` y `Auditoria`.
- **RF3:** solicitudes con validación de fechas, mínimo 30 caracteres, texto de adjunto simulado, permisos superpuestos y vacaciones disponibles. Estados pendiente/aprobado/rechazado, notificación interna, aprobación solo del jefe del área o RRHH.
- **RF4:** autenticación Django, grupos y roles de prueba, controles de acceso en todas las vistas; contador solo reportes. Sesión 2700 segundos (45 min).
- **RF5:** middleware para recordatorio laboral, ventana de marcación referencial (L-V 06:00–19:00), bloqueo de cuenta inactiva, log de cambios y accesos denegados.
- **RF6:** Admin con búsquedas, filtros, cálculos, aprobación masiva y exportación TXT. Auditoría visible únicamente a RRHH.

## Reglas de negocio aclaradas
La guía no fija un horario de trabajo concreto. Para aplicar la tolerancia **±2 horas** se asume **08:00–17:00** (permite marcar entre 06:00 y 19:00, lunes a viernes); ajustar esta política para un entorno real y turnos personalizados. La marcación usa la hora **del servidor**, nunca una fecha enviada por el navegador. Las vacaciones son un **saldo académico simplificado de 30 días menos días aprobados**, no un cálculo de ley laboral peruana, acumulación anual ni derecho adquirido. Los días solicitados se cuentan como días calendario e incluyen ambos extremos. Las 60 asistencias precargadas son datos históricos de demostración y no prueban una operación real.

## Seguridad y límites del prototipo
CSRF en formularios POST, contraseñas Django hasheadas, sesión HttpOnly y Secure cuando `DJANGO_DEBUG=0`, validación del servidor, consultas segmentadas por rol, protección de informes y logs. Para producción configure `DJANGO_SECRET_KEY`, HTTPS, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, permisos de base de datos y validación jurídica/operativa, y reemplace credenciales de demo. Django Admin debe limitarse a personal autorizado; un superusuario técnico puede ver todos los modelos, como es habitual en Django.

La vista de corrección sí registra cambios posteriores a 24 horas para RRHH; el empleado no tiene permisos para corregir registros en ningún momento. La guía exige impedir al empleado modificaciones *después* de 24 horas, lo cual queda cubierto de forma más estricta (nunca puede modificar entradas históricas).

## Pruebas automáticas
```powershell
python manage.py test personal
python manage.py check
```

## Datos de muestra y evidencias
`cargar_demo`: **12 empleados, 5 áreas, 60 asistencias, 12 permisos**. Capture en su computadora: formulario inválido/válido, aprobación, Admin, terminal con auditoría, control de acceso 403 y cookies `sessionid` en DevTools. La carpeta `evidencias/` contiene una lista de las capturas pendientes. No se adjuntan capturas inventadas.


