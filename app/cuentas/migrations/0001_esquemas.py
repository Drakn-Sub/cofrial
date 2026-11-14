"""Crea los esquemas por dominio si no existen.

En AWS ya los crea `infra/sql/01_roles.sql` con el usuario administrador (el rol de
migraciones no tiene permiso CREATE sobre la base). Este paso solo los crea donde
falten, por ejemplo en la base temporal de las pruebas automáticas.
"""
from django.db import migrations

# SQL fijo (sin construir cadenas): crea cada esquema solo si no existe.
SQL = """
DO $$
DECLARE esquema text;
BEGIN
    FOREACH esquema IN ARRAY ARRAY['comercial', 'crm', 'logistica', 'bi', 'seguridad'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = esquema) THEN
            EXECUTE format('CREATE SCHEMA %I', esquema);
        END IF;
    END LOOP;
END $$;
"""


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop)]
