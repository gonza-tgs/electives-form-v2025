"""Decide si el formulario está abierto según los secrets y la hora de Chile.

Secrets:
  FORMULARIO_ABIERTO   interruptor manual. Sin él (o en false) el formulario está cerrado siempre.
  FORMULARIO_APERTURA  opcional, "AAAA-MM-DD HH:MM" en hora de Chile. Antes de esa hora, cerrado.
  FORMULARIO_CIERRE    opcional, "AAAA-MM-DD HH:MM" en hora de Chile. Desde esa hora, cerrado.
"""
import logging
from datetime import datetime
from typing import Mapping, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ = ZoneInfo("America/Santiago")
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

CERRADO = "El proceso de inscripción de electivos está cerrado por ahora."


def parse_fecha(valor) -> datetime:
    return datetime.strptime(str(valor).strip(), "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def fecha_legible(fecha: datetime) -> str:
    return f"el {DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]} a las {fecha:%H:%M}"


def estado_formulario(secrets: Mapping, ahora: Optional[datetime] = None) -> Tuple[bool, str]:
    """Devuelve (abierto, mensaje). El mensaje solo se usa cuando está cerrado."""
    if not secrets.get("FORMULARIO_ABIERTO", False):
        return False, CERRADO
    try:
        apertura = parse_fecha(secrets["FORMULARIO_APERTURA"]) if secrets.get("FORMULARIO_APERTURA") else None
        cierre = parse_fecha(secrets["FORMULARIO_CIERRE"]) if secrets.get("FORMULARIO_CIERRE") else None
    except ValueError:
        # Una fecha mal escrita no debe abrir el formulario antes de tiempo.
        logger.error("FORMULARIO_APERTURA o FORMULARIO_CIERRE no tiene el formato AAAA-MM-DD HH:MM")
        return False, CERRADO

    ahora = ahora or datetime.now(tz=TZ)
    if apertura and ahora < apertura:
        return False, (f"El proceso de inscripción de electivos abre {fecha_legible(apertura)}. "
                       "A esa hora, recarga esta página.")
    if cierre and ahora >= cierre:
        return False, f"El proceso de inscripción de electivos cerró {fecha_legible(cierre)}."
    return True, ""
