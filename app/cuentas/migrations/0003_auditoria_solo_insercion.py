"""La auditoría es de solo inserción: Django puede escribir eventos, pero no modificarlos ni borrarlos."""
from django.db import migrations

SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cofrial_app') THEN
        REVOKE ALL ON seguridad.auditoria_evento FROM cofrial_app;
        GRANT SELECT, INSERT ON seguridad.auditoria_evento TO cofrial_app;
    END IF;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0002_initial")]
    operations = [migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop)]
