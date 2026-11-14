"""Reinicia el segundo factor de una persona que perdió su celular.

    python manage.py reiniciar_2fa vendedor@cofrial.cl

La próxima vez que inicie sesión verá un código QR nuevo. Queda registrado en la auditoría.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice

from cuentas.utils import auditar


class Command(BaseCommand):
    help = "Borra el segundo factor (TOTP) de un usuario para que escanee un código QR nuevo"

    def add_arguments(self, parser):
        parser.add_argument("usuario", help="Nombre de usuario o correo")

    def handle(self, *args, **options):
        usuario = get_user_model().objects.filter(username=options["usuario"]).first()
        if usuario is None:
            raise CommandError(f"No existe el usuario {options['usuario']}")
        borrados, _ = TOTPDevice.objects.filter(user=usuario).delete()
        auditar("2FA_REINICIADO", usuario=usuario, entidad="usuario", entidad_id=usuario.pk, detalle="por administrador")
        self.stdout.write(self.style.SUCCESS(f"Segundo factor reiniciado para {usuario} ({borrados} dispositivo borrado)."))
