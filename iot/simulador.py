"""Simulador de telemetría de la flota de Cofrial (requisito del Hito 2).

Cada camión envía cada INTERVALO_SEG segundos los campos exigidos por el enunciado:
camion_id, temp_camara, lat, long, combustible_pct y alerta_ruptura_frio.

- Conecta a RDS con el rol iot_ingest (solo INSERT en logistica.telemetria) y TLS verify-full.
- Un camión (CAMION_CON_FALLA) sufre una falla de frío de 10 minutos cada hora, para la demo.
- Si la base de datos se reinicia o conmuta (Multi-AZ), reconecta solo.
"""
import logging
import math
import os
import random
import signal
import time
from datetime import datetime, timezone

import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s simulador %(message)s")
log = logging.getLogger()

INTERVALO = int(os.environ.get("INTERVALO_SEG", "30"))
CAMIONES = int(os.environ.get("CAMIONES", "50"))
CON_FALLA = os.environ.get("CAMION_CON_FALLA", "CF-027")
CICLOS_POR_HORA = max(1, 3600 // INTERVALO)
INSERTAR = (
    "INSERT INTO logistica.telemetria (registrado_en, camion_id, temp_camara, lat, long, "
    "combustible_pct, alerta_ruptura_frio) VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
BASE_TEMUCO = (-38.7359, -72.5904)
seguir = True


def detener(*_):
    global seguir
    seguir = False


signal.signal(signal.SIGTERM, detener)
signal.signal(signal.SIGINT, detener)


def dsn():
    partes = {
        "host": os.environ["DB_HOST"],
        "dbname": os.environ.get("DB_NAME", "cofrial"),
        "user": os.environ.get("DB_USER", "iot_ingest"),
        "password": os.environ["DB_PASSWORD"],
        "sslmode": os.environ.get("DB_SSLMODE", "verify-full"),
        "connect_timeout": "10",
        "application_name": "simulador-iot",
    }
    if os.environ.get("DB_SSLROOTCERT"):
        partes["sslrootcert"] = os.environ["DB_SSLROOTCERT"]
    return " ".join(f"{k}={v}" for k, v in partes.items())


class Camion:
    def __init__(self, numero):
        self.id = f"CF-{numero:03d}"
        self.congelado = numero % 2 == 0
        self.objetivo = -19.5 if self.congelado else 2.5
        self.limite_max = -18.0 if self.congelado else 4.0
        self.limite_min = -25.0 if self.congelado else 0.0
        self.temp = self.objetivo + random.uniform(-0.5, 0.5)
        self.lat = BASE_TEMUCO[0] + random.uniform(-0.35, 0.35)
        self.lon = BASE_TEMUCO[1] + random.uniform(-0.45, 0.45)
        self.rumbo = random.uniform(0, 2 * math.pi)
        self.combustible = random.randint(45, 100)

    def leer(self, ciclo):
        en_falla = self.id == CON_FALLA and CICLOS_POR_HORA // 6 <= ciclo % CICLOS_POR_HORA < CICLOS_POR_HORA // 3
        if en_falla:  # el equipo de frío se detiene: la cámara se calienta
            self.temp += random.uniform(0.6, 1.2)
        else:  # el termostato devuelve la cámara a su temperatura objetivo
            self.temp += (self.objetivo - self.temp) * 0.35 + random.uniform(-0.25, 0.25)
        self.temp = max(-30.0, min(30.0, self.temp))
        self.rumbo += random.uniform(-0.35, 0.35)
        self.lat = max(-39.3, min(-38.1, self.lat + 0.0015 * math.cos(self.rumbo)))
        self.lon = max(-73.2, min(-71.9, self.lon + 0.0015 * math.sin(self.rumbo)))
        if random.random() < 0.3:
            self.combustible = self.combustible - 1 if self.combustible > 8 else 100  # recarga
        fuera = not (self.limite_min <= self.temp <= self.limite_max)
        return (
            datetime.now(timezone.utc), self.id, round(self.temp, 1),
            round(self.lat, 6), round(self.lon, 6), self.combustible, fuera,
        )


def main():
    flota = [Camion(n) for n in range(1, CAMIONES + 1)]
    log.info("iniciado: %s camiones, cada %s s, falla simulada en %s", CAMIONES, INTERVALO, CON_FALLA)
    ciclo = 0
    while seguir:
        try:
            with psycopg.connect(dsn()) as conexion:
                log.info("conectado a la base de datos con TLS")
                while seguir:
                    lecturas = [camion.leer(ciclo) for camion in flota]
                    with conexion.cursor() as cursor:
                        cursor.executemany(INSERTAR, lecturas)
                    conexion.commit()
                    fuera = sum(1 for lectura in lecturas if lectura[-1])
                    log.info("ciclo %s: %s lecturas, %s fuera de rango", ciclo, len(lecturas), fuera)
                    ciclo += 1
                    for _ in range(INTERVALO):
                        if not seguir:
                            break
                        time.sleep(1)
        except psycopg.OperationalError as error:
            log.warning("sin conexión (%s); reintento en 10 s", str(error).splitlines()[0])
            time.sleep(10)
    log.info("detenido")


if __name__ == "__main__":
    main()
