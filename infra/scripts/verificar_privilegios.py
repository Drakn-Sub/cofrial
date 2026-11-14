"""Prueba de mínimo privilegio en PostgreSQL.

Se conecta con cada rol e intenta operaciones permitidas y prohibidas. Falla
(código de salida 1) si un rol puede hacer algo que no debería, o no puede hacer
lo que necesita. Se ejecuta en el pipeline de CI y también sirve para la demo:

    DB_HOST=... PW_APP=... PW_IOT=... PW_BI=... python verificar_privilegios.py

Las contraseñas se leen del entorno; en AWS vienen de Secrets Manager.
"""
import os
import sys

import psycopg

HOST = os.environ.get("DB_HOST", "localhost")
BASE = os.environ.get("DB_NAME", "cofrial")
SSL = os.environ.get("DB_SSLMODE", "prefer")
ROOTCERT = os.environ.get("DB_SSLROOTCERT", "")

# (rol, variable de contraseña, sentencia SQL, ¿debe permitirse?, descripción)
CASOS = [
    ("cofrial_app", "PW_APP", "SELECT count(*) FROM comercial.cuentas_cliente", True, "Django lee clientes"),
    ("cofrial_app", "PW_APP", "SELECT count(*) FROM logistica.telemetria", True, "Django lee telemetría"),
    ("cofrial_app", "PW_APP", "INSERT INTO seguridad.auditoria_evento (accion, entidad, entidad_id, resultado, detalle, ocurrido_en) VALUES ('PRUEBA','','','OK','verificar_privilegios', now())", True, "Django registra auditoría"),
    ("cofrial_app", "PW_APP", "UPDATE seguridad.auditoria_evento SET resultado = 'X'", False, "Django NO modifica la auditoría"),
    ("cofrial_app", "PW_APP", "DELETE FROM seguridad.auditoria_evento", False, "Django NO borra la auditoría"),
    ("cofrial_app", "PW_APP", "DROP TABLE comercial.order_order", False, "Django NO borra tablas"),
    ("cofrial_app", "PW_APP", "TRUNCATE comercial.cuentas_cliente", False, "Django NO vacía tablas"),
    ("cofrial_app", "PW_APP", "CREATE TABLE comercial.intruso (id int)", False, "Django NO crea tablas"),
    ("cofrial_app", "PW_APP", "INSERT INTO logistica.telemetria (registrado_en, camion_id, temp_camara, lat, long, combustible_pct, alerta_ruptura_frio) VALUES (now(), 'CF-001', 0, 0, 0, 50, false)", False, "Django NO inventa telemetría"),
    ("iot_ingest", "PW_IOT", "INSERT INTO logistica.telemetria (registrado_en, camion_id, temp_camara, lat, long, combustible_pct, alerta_ruptura_frio) VALUES (now(), 'CF-001', 2.5, -38.7, -72.6, 80, false)", True, "IoT inserta telemetría"),
    ("iot_ingest", "PW_IOT", "SELECT * FROM comercial.cuentas_cliente", False, "IoT NO lee clientes"),
    ("iot_ingest", "PW_IOT", "SELECT * FROM logistica.telemetria", False, "IoT NO lee telemetría"),
    ("iot_ingest", "PW_IOT", "DELETE FROM logistica.telemetria", False, "IoT NO borra telemetría"),
    ("iot_ingest", "PW_IOT", "SELECT * FROM comercial.auth_user", False, "IoT NO lee usuarios ni contraseñas"),
    ("bi_reader", "PW_BI", "SELECT * FROM comercial.auth_user", False, "Metabase NO lee usuarios"),
    ("bi_reader", "PW_BI", "SELECT * FROM comercial.cuentas_cliente", False, "Metabase NO lee datos personales"),
    ("bi_reader", "PW_BI", "SELECT * FROM comercial.order_order", False, "Metabase NO lee pedidos con detalle"),
    ("bi_reader", "PW_BI", "SELECT * FROM bi.v_ventas_por_canal", True, "Metabase lee ventas agregadas"),
    ("bi_reader", "PW_BI", "SELECT * FROM bi.v_ultima_posicion", True, "Metabase lee la posición de la flota"),
    ("bi_reader", "PW_BI", "CREATE VIEW bi.intrusa AS SELECT 1", False, "Metabase NO crea objetos"),
]


def conectar(rol, clave):
    params = {"host": HOST, "dbname": BASE, "user": rol, "password": clave, "sslmode": SSL, "connect_timeout": 10}
    if ROOTCERT:
        params["sslrootcert"] = ROOTCERT
    return psycopg.connect(**params)


def probar(rol, clave, sql):
    """Ejecuta dentro de una transacción que siempre se revierte: la prueba no deja rastros."""
    with conectar(rol, clave) as conexion:
        try:
            conexion.execute(sql)
            return True, ""
        except psycopg.errors.InsufficientPrivilege as error:
            return False, str(error).splitlines()[0]
        finally:
            conexion.rollback()


def main():
    fallas = 0
    for rol, variable, sql, permitido, descripcion in CASOS:
        clave = os.environ.get(variable)
        if not clave:
            print(f"OMITIDA  {descripcion} (falta {variable})")
            continue
        resultado, detalle = probar(rol, clave, sql)
        correcto = resultado == permitido
        fallas += 0 if correcto else 1
        marca = "OK      " if correcto else "FALLA   "
        efecto = "permitido" if resultado else f"denegado ({detalle})"
        print(f"{marca}{rol:<12} {descripcion:<38} -> {efecto}")
    print(f"\n{len(CASOS) - fallas} de {len(CASOS)} controles correctos")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
