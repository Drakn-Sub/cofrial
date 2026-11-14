from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil
from .utils import auditar


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.get_or_create(usuario=instance)


@receiver(user_logged_in)
def login_ok(sender, request, user, **kwargs):
    auditar("LOGIN", request, usuario=user, entidad="usuario", entidad_id=user.pk)


@receiver(user_logged_out)
def logout(sender, request, user, **kwargs):
    if user is not None:
        auditar("LOGOUT", request, usuario=user, entidad="usuario", entidad_id=user.pk)


@receiver(user_login_failed)
def login_fallido(sender, credentials, request=None, **kwargs):
    # No se guarda la contraseña intentada, solo el identificador usado.
    identificador = credentials.get("username") or credentials.get("email") or ""
    auditar("LOGIN_FALLIDO", request, entidad="usuario", entidad_id=identificador, resultado="RECHAZADO")
