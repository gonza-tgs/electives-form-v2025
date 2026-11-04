"""Prueba el formulario completo contra la base de pruebas, sin enviar correos reales."""
import os
from pathlib import Path

import psycopg
from streamlit.testing.v1 import AppTest

ADMIN_URL = os.environ["TEST_ADMIN_URL"]
APP_URL = os.environ["TEST_APP_URL"]
ROOT = Path(__file__).resolve().parent.parent
RUN = "10000001-5"
EMAIL = "e1@example.invalid"


def prepare_database():
    with psycopg.connect(ADMIN_URL) as conn:
        assert conn.execute("SELECT current_database()").fetchone()[0].endswith("_test")
        conn.execute(
            "TRUNCATE public.enrollments, public.enrollments_ge, public.students, "
            "public.electives, public.general_edu, public.class RESTART IDENTITY CASCADE"
        )
        conn.execute("INSERT INTO public.class (id, level, name, year) VALUES (3, 3, 'green', 2026), (4, 3, 'blue', 2026)")
        conn.execute(
            "INSERT INTO public.electives "
            "(id, name, area, group_3medio, group_4medio, enabled_3medio, enabled_4medio) VALUES "
            "(1, 'Uno', 'A', 1, 1, true, true), (2, 'Dos', 'B', 2, 2, true, true), (3, 'Tres', 'C', 3, 3, true, true), "
            "(4, 'Oculto', 'C', 3, 3, false, false)"
        )
        conn.execute("INSERT INTO public.general_edu (id, name, enabled_3medio, enabled_4medio) VALUES (1, 'FG uno', 1, 1)")
        conn.execute(
            'INSERT INTO public.students ("RUN", name, lastname, class_id, email) '
            "VALUES ('100000015', 'Nombre', 'Ficticio', 3, %s)",
            (EMAIL,),
        )


def make_app():
    os.chdir(ROOT)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    app.secrets["FORMULARIO_ABIERTO"] = True
    app.secrets["DATABASE_URL"] = APP_URL
    app.secrets["LEVEL"] = "enabled_4medio"
    app.secrets["PROCESS_YEAR"] = 2027
    app.secrets["CUPOS"] = 30
    app.secrets["CUPO_FG"] = 100
    app.secrets["CURSOS"] = ["2 medio G", "2 medio B", "3 medio G", "3 medio B"]
    app.secrets["ELECTIVOS_FG"] = ["FG uno", "FG dos", "FG uno", "FG dos"]
    app.secrets["SENDER_EMAIL"] = "test@example.invalid"
    app.secrets["SENDER_PASSWORD"] = "unused"
    # Nada escucha aquí: el correo falla enseguida y no sale de la máquina.
    app.secrets["SMTP_SERVER"] = "127.0.0.1"
    app.secrets["SMTP_PORT"] = 1
    return app


def fill_and_submit(app):
    app.text_input[0].set_value("Nombre Ficticio")
    app.text_input[1].set_value(RUN)
    app.text_input[2].set_value(EMAIL)
    app.radio[0].set_value("3 medio G")
    app.radio[1].set_value("Área A: Uno")
    app.radio[2].set_value("Área B: Dos")
    app.radio[3].set_value("Área C: Tres")
    app.radio[4].set_value("FG uno")
    app.button[0].click()
    return app.run()


def test_formulario_inscribe_y_bloquea_el_boton():
    prepare_database()
    app = make_app().run()
    assert not app.exception
    assert "Área C: Oculto" not in app.radio[3].options

    app = fill_and_submit(app)
    assert not app.exception
    assert [s.value for s in app.success] == ["¡Inscripción exitosa! Tus respuestas han sido guardadas."]
    assert app.button[0].disabled

    with psycopg.connect(ADMIN_URL) as conn:
        assert conn.execute("SELECT count(*) FROM public.enrollments").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM public.enrollments_ge").fetchone()[0] == 1


def test_formulario_cerrado_muestra_aviso_sin_tocar_la_base():
    app = make_app()
    del app.secrets["FORMULARIO_ABIERTO"]
    app.secrets["DATABASE_URL"] = "postgresql://nadie@127.0.0.1:1/inexistente"
    app.run()
    assert not app.exception
    assert [i.value for i in app.info] == ["El proceso de inscripción de electivos está cerrado por ahora."]
    assert len(app.radio) == 0
    assert len(app.text_input) == 0
    assert len(app.button) == 0
