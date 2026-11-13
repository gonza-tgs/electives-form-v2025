"""Apertura y cierre programados del formulario. No usa base de datos."""
import os
from datetime import datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

from apertura import CERRADO, TZ, estado_formulario

ROOT = Path(__file__).resolve().parent.parent
PROGRAMADO = {
    "FORMULARIO_ABIERTO": True,
    "FORMULARIO_APERTURA": "2026-11-17 18:00",
    "FORMULARIO_CIERRE": "2026-11-18 18:00",
}


def hora(texto):
    return datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)


def test_sin_interruptor_queda_cerrado_aunque_sea_la_hora():
    secrets = dict(PROGRAMADO, FORMULARIO_ABIERTO=False)
    assert estado_formulario(secrets, hora("2026-11-17 18:30:00")) == (False, CERRADO)
    assert estado_formulario({}, hora("2026-11-17 18:30:00")) == (False, CERRADO)


def test_antes_de_la_apertura_avisa_dia_y_hora():
    abierto, aviso = estado_formulario(PROGRAMADO, hora("2026-11-17 17:59:59"))
    assert not abierto
    assert "abre el martes 17 de noviembre a las 18:00" in aviso


def test_abre_justo_a_la_hora_y_cierra_justo_a_la_hora():
    assert estado_formulario(PROGRAMADO, hora("2026-11-17 18:00:00"))[0]
    assert estado_formulario(PROGRAMADO, hora("2026-11-18 17:59:59"))[0]
    abierto, aviso = estado_formulario(PROGRAMADO, hora("2026-11-18 18:00:00"))
    assert not abierto
    assert "cerró el miércoles 18 de noviembre a las 18:00" in aviso


def test_la_hora_es_la_de_chile_aunque_el_servidor_este_en_utc():
    # 21:00 UTC = 18:00 en Chile en noviembre (horario de verano, UTC-3).
    assert estado_formulario(PROGRAMADO, datetime.fromisoformat("2026-11-17T21:00:00+00:00"))[0]
    assert not estado_formulario(PROGRAMADO, datetime.fromisoformat("2026-11-17T20:59:00+00:00"))[0]


def test_sin_fechas_manda_solo_el_interruptor():
    assert estado_formulario({"FORMULARIO_ABIERTO": True}, hora("2030-01-01 00:00:00")) == (True, "")


def test_fecha_mal_escrita_no_abre():
    secrets = dict(PROGRAMADO, FORMULARIO_APERTURA="17-11-2026 18:00")
    assert estado_formulario(secrets, hora("2026-11-17 18:30:00")) == (False, CERRADO)


def test_app_antes_de_la_apertura_muestra_aviso_sin_tocar_la_base():
    os.chdir(ROOT)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    app.secrets["FORMULARIO_ABIERTO"] = True
    app.secrets["FORMULARIO_APERTURA"] = "2099-11-17 18:00"
    app.secrets["DATABASE_URL"] = "postgresql://nadie@127.0.0.1:1/inexistente"
    # form_validate.py los lee al importarse, antes de revisar la apertura.
    app.secrets["CUPOS"] = 30
    app.secrets["CUPO_FG"] = 100
    app.secrets["PROCESS_YEAR"] = 2027
    app.run()
    assert not app.exception
    assert [i.value for i in app.info] == [
        "El proceso de inscripción de electivos abre el martes 17 de noviembre a las 18:00. "
        "A esa hora, recarga esta página."
    ]
    assert len(app.radio) == 0
    assert len(app.button) == 0
