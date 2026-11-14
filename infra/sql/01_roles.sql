-- Esquemas por dominio y roles de mínimo privilegio (Tabla 9 del informe).
-- Idempotente: se puede ejecutar varias veces; crea lo que falte y sincroniza las contraseñas.
-- Se ejecuta con el usuario administrador de RDS: infra/scripts/inicializar_bd.sh lo hace leyendo
-- las contraseñas desde Secrets Manager. Llegan como variables de psql (:'pw_app', etc.);
-- nunca se escriben en este archivo.

CREATE SCHEMA IF NOT EXISTS comercial;
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS logistica;
CREATE SCHEMA IF NOT EXISTS bi;
CREATE SCHEMA IF NOT EXISTS seguridad;

-- Nadie crea objetos en public por accidente
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER DATABASE cofrial SET search_path = comercial, public;

-- Crea los roles que falten (sin contraseña todavía)
SELECT format('CREATE ROLE %I LOGIN', r)
FROM unnest(ARRAY['cofrial_migrate', 'cofrial_app', 'iot_ingest', 'bi_reader', 'metabase_app']) AS r
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) \gexec

-- Contraseñas desde Secrets Manager y límites de conexión
ALTER ROLE cofrial_migrate PASSWORD :'pw_migrate';
ALTER ROLE cofrial_app PASSWORD :'pw_app';
ALTER ROLE iot_ingest PASSWORD :'pw_iot' CONNECTION LIMIT 5;
ALTER ROLE bi_reader PASSWORD :'pw_bi' CONNECTION LIMIT 10;
ALTER ROLE metabase_app PASSWORD :'pw_metabase';

-- 1. Migraciones: crea y modifica tablas (solo se usa al desplegar)
GRANT CONNECT ON DATABASE cofrial TO cofrial_migrate;
GRANT USAGE, CREATE ON SCHEMA comercial, crm, logistica, bi, seguridad TO cofrial_migrate;
GRANT cofrial_migrate TO CURRENT_USER;  -- necesario en RDS para ALTER DEFAULT PRIVILEGES

-- 2. Django en operación: lee y escribe datos, sin DDL (no puede DROP, ALTER ni TRUNCATE)
GRANT CONNECT ON DATABASE cofrial TO cofrial_app;
GRANT USAGE ON SCHEMA comercial, crm, logistica, seguridad TO cofrial_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cofrial_migrate IN SCHEMA comercial, crm, logistica
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cofrial_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cofrial_migrate IN SCHEMA comercial, crm, logistica, seguridad
  GRANT USAGE, SELECT ON SEQUENCES TO cofrial_app;
-- En "seguridad" no hay privilegios por defecto: la auditoría recibe solo SELECT e INSERT (migración).

-- 3. Simulador IoT: solo puede insertar telemetría (permiso explícito en la migración de la tabla)
GRANT CONNECT ON DATABASE cofrial TO iot_ingest;
GRANT USAGE ON SCHEMA logistica TO iot_ingest;

-- 4. Metabase: solo lee las vistas del esquema bi (sin datos personales)
GRANT CONNECT ON DATABASE cofrial TO bi_reader;
GRANT USAGE ON SCHEMA bi TO bi_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE cofrial_migrate IN SCHEMA bi GRANT SELECT ON TABLES TO bi_reader;
ALTER ROLE bi_reader SET search_path = bi;

-- 5. Metabase guarda su propia configuración en otra base de datos
GRANT metabase_app TO CURRENT_USER;
SELECT 'CREATE DATABASE metabase OWNER metabase_app'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'metabase') \gexec
