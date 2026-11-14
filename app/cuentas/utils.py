"""Utilidades compartidas: IP del cliente y registro de auditoría."""
import logging

logger = logging.getLogger("cofrial.auditoria")


def ip_cliente(request, *args, **kwargs):
    """IP real del cliente.

    Django solo es alcanzable a través de Nginx (red interna de Docker), y Nginx
    resuelve la IP real a partir de X-Forwarded-For del balanceador y la entrega
    en X-Real-IP. Por eso se confía en esa cabecera y no en lo que envíe el navegador.
    """
    if request is None:
        return None
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def auditar(accion, request=None, usuario=None, entidad="", entidad_id="", resultado="OK", detalle=""):
    """Inserta un evento de auditoría. Nunca interrumpe la operación del usuario si falla."""
    from .models import AuditoriaEvento

    if usuario is None and request is not None and getattr(request, "user", None) is not None:
        usuario = request.user if request.user.is_authenticated else None
    try:
        AuditoriaEvento.objects.create(
            usuario=usuario,
            accion=accion[:40],
            entidad=entidad[:40],
            entidad_id=str(entidad_id)[:64],
            ip_origen=ip_cliente(request),
            resultado=resultado[:10],
            detalle=detalle[:200],
        )
    except Exception:  # la auditoría también va a los registros de CloudWatch
        logger.exception("No se pudo registrar el evento de auditoría %s", accion)
    logger.info("auditoria accion=%s entidad=%s id=%s resultado=%s", accion, entidad, entidad_id, resultado)
