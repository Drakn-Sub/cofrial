"""Proceso de la torre de control. Corre en ambos nodos; solo uno evalúa en cada ciclo.

La coordinación usa un bloqueo consultivo de PostgreSQL (pg_try_advisory_lock): sin
Redis ni otro servicio, y si un nodo se cae, el otro toma el bloqueo en el siguiente ciclo.
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection

from logistica.alertas import evaluar

CANDADO = 727001
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Abre y cierra alertas de ruptura de frío a partir de la telemetría"

    def add_arguments(self, parser):
        parser.add_argument("--intervalo", type=int, default=30)
        parser.add_argument("--una-vez", action="store_true", help="Evalúa un solo ciclo y termina")

    def handle(self, *args, intervalo, una_vez, **options):
        self.seguir = True
        signal.signal(signal.SIGTERM, self._detener)
        while self.seguir:
            close_old_connections()  # reconecta si RDS conmutó a la réplica
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_try_advisory_lock(%s)", [CANDADO])
                    soy_lider = cursor.fetchone()[0]
                if soy_lider:
                    try:
                        abiertas, cerradas = evaluar()
                        if abiertas or cerradas:
                            logger.info("alertas abiertas=%s cerradas=%s", abiertas, cerradas)
                    finally:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT pg_advisory_unlock(%s)", [CANDADO])
            except Exception:
                logger.exception("Error en el ciclo de evaluación; se reintenta en el siguiente")
            if una_vez:
                break
            time.sleep(intervalo)

    def _detener(self, *args):
        self.seguir = False
