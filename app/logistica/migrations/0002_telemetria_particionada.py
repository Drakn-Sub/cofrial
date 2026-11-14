"""Telemetría particionada por mes con índice BRIN, y permisos de mínimo privilegio.

50 camiones x 2 lecturas por minuto = ~4,3 millones de filas al mes. Particionar por mes
permite borrar meses antiguos sin bloquear la tabla, y BRIN indexa el tiempo con muy
poco espacio porque las lecturas llegan ordenadas.
"""
from django.db import migrations

CREAR = """
CREATE TABLE logistica.telemetria (
    telemetria_id       BIGINT GENERATED ALWAYS AS IDENTITY,
    registrado_en       TIMESTAMPTZ NOT NULL,
    camion_id           VARCHAR(10) NOT NULL REFERENCES logistica.camion (camion_id),
    temp_camara         NUMERIC(4,1) NOT NULL CHECK (temp_camara BETWEEN -40 AND 40),
    lat                 NUMERIC(9,6) NOT NULL CHECK (lat BETWEEN -90 AND 90),
    long                NUMERIC(9,6) NOT NULL CHECK (long BETWEEN -180 AND 180),
    combustible_pct     SMALLINT NOT NULL CHECK (combustible_pct BETWEEN 0 AND 100),
    alerta_ruptura_frio BOOLEAN NOT NULL,
    recibido_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (telemetria_id, registrado_en)
) PARTITION BY RANGE (registrado_en);

CREATE TABLE logistica.telemetria_2026_11 PARTITION OF logistica.telemetria
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE logistica.telemetria_2026_12 PARTITION OF logistica.telemetria
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
CREATE TABLE logistica.telemetria_2027_01 PARTITION OF logistica.telemetria
    FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
CREATE TABLE logistica.telemetria_default PARTITION OF logistica.telemetria DEFAULT;

CREATE INDEX telemetria_tiempo_brin ON logistica.telemetria USING BRIN (registrado_en);
CREATE INDEX telemetria_camion_tiempo ON logistica.telemetria (camion_id, registrado_en DESC);

-- Mínimo privilegio: el simulador solo inserta; Django solo lee la telemetría.
DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT 'logistica.' || c.relname FROM pg_class c
             JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'logistica' AND c.relname LIKE 'telemetria%' AND c.relkind IN ('r', 'p')
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cofrial_app') THEN
            EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON %s FROM cofrial_app', t);
            EXECUTE format('GRANT SELECT ON %s TO cofrial_app', t);
        END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'iot_ingest') THEN
        GRANT INSERT ON logistica.telemetria TO iot_ingest;
        -- Las restricciones de llave foránea necesitan leer el código del camión
        GRANT SELECT (camion_id) ON logistica.camion TO iot_ingest;
    END IF;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [("logistica", "0001_initial")]
    operations = [migrations.RunSQL(CREAR, reverse_sql="DROP TABLE IF EXISTS logistica.telemetria CASCADE;")]
