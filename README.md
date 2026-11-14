# Cofrial SpA · Transformación digital de la cadena de frío

Proyecto de la asignatura Transformación Digital (TIEL15), INACAP Sede Temuco.
Equipo: **Benjamín Aguilar** y **Daniel Jara**.

Plataforma única para una distribuidora de alimentos refrigerados de La Araucanía:
tienda B2B/B2C, CRM, torre de control con telemetría IoT y tablero de BI, desplegada
en AWS con un enfoque de seguridad desde el diseño (DevSecOps).

## Componentes

| Carpeta | Qué contiene |
| --- | --- |
| `app/` | Proyecto Django 5.2 con django-oscar 4.0 (tienda), `cuentas` (clientes, precios de convenio, 2FA, auditoría), `crm` (embudo kanban e IA) y `logistica` (torre de control) |
| `iot/` | Simulador de telemetría de 50 camiones (Python, Docker) |
| `infra/sql/` | Esquemas y roles de mínimo privilegio de PostgreSQL |
| `infra/scripts/` | Despliegue en EC2 por Session Manager, leyendo secretos desde Secrets Manager, y verificación de privilegios |
| `infra/nginx/`, `infra/compose.*.yml` | Proxy inverso y contenedores endurecidos |
| `.github/workflows/` | Pipeline DevSecOps y análisis OWASP ZAP |
| `docs/` | Auditoría de la infraestructura, correcciones y evidencias |

## Arquitectura en AWS

```
Internet ─► ALB (443, TLS) ─► Nginx + Django en 2 zonas (subredes privadas) ─► RDS PostgreSQL Multi-AZ
                                          ▲
                Simulador IoT (subred privada, rol iot_ingest) ─┘
```

- Solo el balanceador es público. Los servidores no tienen IP pública ni SSH: se administran con Session Manager.
- Security Groups encadenados: ALB → aplicación → base de datos.
- Secretos en Secrets Manager; la contraseña maestra de RDS la gestiona AWS.
- Discos, base de datos y bucket S3 cifrados; TLS `verify-full` hasta PostgreSQL.

## Seguridad verificable

| Control | Cómo se comprueba |
| --- | --- |
| Mínimo privilegio por rol | `python infra/scripts/verificar_privilegios.py` (16 controles) |
| Pruebas de negocio y seguridad | `python app/manage.py test cuentas crm logistica` (22 pruebas: precios, IDOR, 2FA, IA, alertas) |
| Secretos, SAST, dependencias | Pipeline `ci-seguridad` en cada push (Gitleaks, Bandit, pip-audit + SBOM) |
| Configuración de Django | `python app/manage.py check --deploy` |
| Superficie expuesta | Prueba TCP desde fuera de la VPC (ver `docs/01-auditoria-inicial.md`) |

## Desarrollo local

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# PostgreSQL 16 local con los roles de infra/sql/01_roles.sql
export SECRET_KEY=solo-desarrollo DEBUG=1 DB_USER=cofrial_migrate DB_PASSWORD=...
python manage.py migrate
export DB_USER=cofrial_app DB_PASSWORD=...
python manage.py cargar_demo
python manage.py runserver
```

## Uso de herramientas de IA

El equipo usó un asistente de IA (Claude) como apoyo en la auditoría, el código y la
documentación. Las decisiones de arquitectura, la operación de las cuentas y la
validación de cada control fueron realizadas y revisadas por el equipo.
