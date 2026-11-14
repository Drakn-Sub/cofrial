-- Esquemas por dominio y roles de mínimo privilegio (Tabla 9 del informe).
-- Se ejecuta UNA vez con el usuario administrador de RDS (cofrial_admin):
--   infra/scripts/inicializar_bd.sh lo hace leyendo las contraseñas desde Secrets Manager.
-- Las contraseñas llegan como variables de psql (:'pw_app', etc.); nunca se escriben aquí.

CREATE SCHEMA IF NOT EXISTS comercial;
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS logistica;
CREATE SCHEMA IF NOT EXISTS bi;
CREATE SCHEMA IF NOT EXISTS seguridad;

-- Nadie crea objetos en public por accidente
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER DATABASE cofrial SET search_path = comercial, public;

-- 1. Migraciones: crea y modifica tablas (solo se usa al desplegar)
CREATE ROLE cofrial_migrate LOGIN PASSWORD :'pw_migrate';
GRANT CONNECT ON DATABASE cofrial TO cofrial_migrate;
GRANT USAGE, CREATE ON SCHEMA comercial, crm, logistica, bi, seguridad TO cofrial_migrate;
GRANT cofrial_migrate TO CURRENT_USER;  -- necesario en RDS para ALTER DEFAULT PRIVILEGES

-- 2. Django en operación: lee y escribe datos, sin DDL (no puede DROP, ALTER ni TRUNCATE)
CREATE ROLE cofrial_app LOGIN PASSWORD :'pw_app';
GRANT CONNECT ON DATABASE cofrial TO cofrial_app;
GRANT USAGE ON SCHEMA comercial, crm, logistica, seguridad TO cofrial_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cofrial_migrate IN SCHEMA comercial, crm, logistica
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cofrial_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cofrial_migrate IN SCHEMA comercial, crm, logistica, seguridad
  GRANT USAGE, SELECT ON SEQUENCES TO cofrial_app;
-- En "seguridad" no hay privilegios por defecto: la auditoría recibe solo SELECT e INSERT (migración).

-- 3. Simulador IoT: solo puede insertar telemetría (permiso explícito en la migración de la tabla)
CREATE ROLE iot_ingest LOGIN PASSWORD :'pw_iot' CONNECTION LIMIT 5;
GRANT CONNECT ON DATABASE cofrial TO iot_ingest;
GRANT USAGE ON SCHEMA logistica TO iot_ingest;

-- 4. Metabase: solo lee las vistas del esquema bi (sin datos personales)
CREATE ROLE bi_reader LOGIN PASSWORD :'pw_bi' CONNECTION LIMIT 10;
GRANT CONNECT ON DATABASE cofrial TO bi_reader;
GRANT USAGE ON SCHEMA bi TO bi_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE cofrial_migrate IN SCHEMA bi GRANT SELECT ON TABLES TO bi_reader;
ALTER ROLE bi_reader SET search_path = bi;

-- 5. Metabase guarda su propia configuración en otra base de datos
CREATE ROLE metabase_app LOGIN PASSWORD :'pw_metabase';
GRANT metabase_app TO CURRENT_USER;
CREATE DATABASE metabase OWNER metabase_app;
