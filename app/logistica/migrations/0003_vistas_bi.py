"""Vistas del esquema bi para Metabase.

Metabase se conecta con el rol bi_reader, que solo puede leer estas vistas. Las vistas
son del dueño (cofrial_migrate) y se ejecutan con sus permisos, así bi_reader ve datos
agregados sin tener acceso a las tablas de clientes, usuarios ni contraseñas.
Las tablas comerciales se resuelven con el search_path (comercial, public).
Ninguna vista expone nombres, RUT, correos ni direcciones (Ley 19.628 / 21.719).
"""
from django.db import migrations

VISTAS = """
-- 1. Ventas por día y canal (B2B convenio / B2C público)
CREATE OR REPLACE VIEW bi.v_ventas_por_canal AS
SELECT (o.date_placed AT TIME ZONE 'America/Santiago')::date AS dia,
       COALESCE(c.tipo, 'B2C')                              AS canal,
       count(*)                                             AS pedidos,
       sum(o.total_incl_tax)                                AS total_clp
FROM order_order o
LEFT JOIN cuentas_perfil p  ON p.usuario_id = o.user_id
LEFT JOIN cuentas_cliente c ON c.id = p.cliente_id
WHERE o.status <> 'Anulado'
GROUP BY 1, 2;

-- 2. Última posición y temperatura de cada camión (mapa de la flota)
CREATE OR REPLACE VIEW bi.v_ultima_posicion AS
SELECT DISTINCT ON (t.camion_id)
       t.camion_id, cam.regimen, t.registrado_en, t.temp_camara,
       t.lat AS latitud, t.long AS longitud, t.combustible_pct, t.alerta_ruptura_frio
FROM logistica.telemetria t
JOIN logistica.camion cam ON cam.camion_id = t.camion_id
WHERE t.registrado_en > now() - interval '2 hours'
ORDER BY t.camion_id, t.registrado_en DESC;

-- 3. Alertas de ruptura de la cadena de frío y su duración
CREATE OR REPLACE VIEW bi.v_alertas AS
SELECT a.id AS alerta_id, a.camion_id, cam.regimen, a.estado,
       a.inicio_en, a.fin_en, a.temp_extrema,
       round(extract(epoch FROM coalesce(a.fin_en, now()) - a.inicio_en) / 60) AS minutos
FROM logistica.alerta_frio a
JOIN logistica.camion cam ON cam.camion_id = a.camion_id;

-- 4. Pedidos afectados por una alerta (sin datos del cliente)
CREATE OR REPLACE VIEW bi.v_pedidos_afectados AS
SELECT o.number AS pedido, o.status AS estado, o.date_placed AS fecha,
       o.total_incl_tax AS total_clp, COALESCE(c.tipo, 'B2C') AS canal, d.camion_id
FROM order_order o
LEFT JOIN cuentas_perfil p        ON p.usuario_id = o.user_id
LEFT JOIN cuentas_cliente c       ON c.id = p.cliente_id
LEFT JOIN logistica.despacho_pedido dp      ON dp.pedido_id = o.id
LEFT JOIN logistica.despacho d              ON d.id = dp.despacho_id
WHERE o.status = 'En ruta con alerta';

-- 5. Embudo comercial del CRM por etapa
CREATE OR REPLACE VIEW bi.v_pipeline_crm AS
SELECT e.orden, e.nombre AS etapa, e.probabilidad_pct,
       count(op.id)                                                AS oportunidades,
       coalesce(sum(op.monto_estimado), 0)                         AS monto_clp,
       coalesce(sum(op.monto_estimado * e.probabilidad_pct / 100), 0) AS monto_ponderado_clp
FROM crm.etapa_pipeline e
LEFT JOIN crm.oportunidad op ON op.etapa_id = e.id
GROUP BY e.orden, e.nombre, e.probabilidad_pct;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bi_reader') THEN
        GRANT USAGE ON SCHEMA bi TO bi_reader;
        GRANT SELECT ON ALL TABLES IN SCHEMA bi TO bi_reader;
    END IF;
END $$;
"""

BORRAR = """
DROP VIEW IF EXISTS bi.v_pipeline_crm, bi.v_pedidos_afectados, bi.v_alertas,
                    bi.v_ultima_posicion, bi.v_ventas_por_canal;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("logistica", "0002_telemetria_particionada"),
        ("cuentas", "0003_auditoria_solo_insercion"),
        ("crm", "0002_initial"),
        ("order", "0018_alter_line_num_allocated"),
    ]
    operations = [migrations.RunSQL(VISTAS, reverse_sql=BORRAR)]
