"""Pruebas de la función de inscripción contra un Postgres desechable, con datos ficticios.

Requiere TEST_ADMIN_URL y TEST_APP_URL. Borra las tablas, así que exige que la base
se llame *_test.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

ADMIN_URL = os.environ["TEST_ADMIN_URL"]
APP_URL = os.environ["TEST_APP_URL"]
YEAR = 2027
CALL = """
    SELECT public.validar_e_inscribir_electivos(
        %s, %s, %s, %s, %s, %s, %s, %s::integer, %s::integer, %s::integer
    )
"""
E1, E2, E3 = "Área A: Uno", "Área B: Dos", "Área C: Tres"
ALT1 = "Área A: Uno alternativo"


def run_of(n):
    return f"{10000000 + n}-5"


def clean_run(n):
    return f"{10000000 + n}5"


def email_of(n):
    return f"e{n}@example.invalid"


def form(n, e1=E1, e2=E2, e3=E3, fg="FG uno", cupos=100, cupos_fg=100, curso="2 medio G", year=YEAR):
    return (run_of(n), email_of(n), curso, e1, e2, e3, fg, year, cupos, cupos_fg)


@pytest.fixture(autouse=True)
def fixture_data():
    with psycopg.connect(ADMIN_URL) as conn:
        dbname = conn.execute("SELECT current_database()").fetchone()[0]
        assert dbname.endswith("_test"), "Estas pruebas solo corren en una base *_test"
        conn.execute(
            "TRUNCATE public.enrollments, public.enrollments_ge, public.students, "
            "public.electives, public.general_edu, public.class RESTART IDENTITY CASCADE"
        )
        conn.execute(
            "INSERT INTO public.class (id, level, name, year) VALUES "
            "(1, 2, 'green', 2026), (2, 2, 'blue', 2026), (3, 3, 'green', 2026), (4, 3, 'blue', 2026)"
        )
        conn.execute(
            "INSERT INTO public.electives "
            "(id, name, area, group_3medio, group_4medio, enabled_3medio, enabled_4medio) VALUES "
            "(1, 'Uno', 'A', 1, 1, true, true), (2, 'Dos', 'B', 2, 2, true, true), "
            "(3, 'Tres', 'C', 3, 3, true, true), (4, 'Uno alternativo', 'A', 1, 1, true, true), "
            "(5, 'Dos en A', 'A', 2, 2, true, true), (6, 'Tres en A', 'A', 3, 3, true, true)"
        )
        conn.execute(
            "INSERT INTO public.general_edu (id, name, enabled_3medio, enabled_4medio) VALUES "
            "(1, 'FG uno', 1, 1), (2, 'FG dos', 1, 1)"
        )
        for n in range(60):
            conn.execute(
                'INSERT INTO public.students ("RUN", name, lastname, class_id, email) '
                "VALUES (%s, 'Nombre', 'Ficticio', 1, %s)",
                (clean_run(n), email_of(n)),
            )


def call(args):
    with psycopg.connect(APP_URL) as conn:
        return conn.execute(CALL, args).fetchone()[0]


def call_all_at_once(forms):
    """Abre las conexiones antes y dispara todas las llamadas juntas."""
    barrier = Barrier(len(forms))
    conns = [psycopg.connect(APP_URL) for _ in forms]

    def worker(item):
        conn, args = item
        barrier.wait()
        with conn:
            return conn.execute(CALL, args).fetchone()[0]

    with ThreadPoolExecutor(max_workers=len(forms)) as pool:
        return list(pool.map(worker, zip(conns, forms)))


def scalar(sql, params=()):
    with psycopg.connect(ADMIN_URL) as conn:
        return conn.execute(sql, params).fetchone()[0]


def enrolled(elective_id):
    return scalar(
        "SELECT count(*) FROM public.enrollments WHERE elective_id = %s AND process_year = %s",
        (elective_id, YEAR),
    )


def test_concurrente_mismo_envio_queda_una_vez():
    results = call_all_at_once([form(1)] * 25)
    assert all(r["valido"] for r in results), results
    assert scalar("SELECT count(*) FROM public.enrollments") == 3
    assert scalar("SELECT count(*) FROM public.enrollments_ge") == 1


def test_concurrente_selecciones_distintas_gana_una():
    forms = [form(1), form(1, e1=ALT1)] * 12
    results = call_all_at_once(forms)
    assert sum(r["mensaje"] == "Inscripción exitosa." for r in results) == 1
    assert not any("Error interno" in r["mensaje"] for r in results), results
    assert scalar("SELECT count(*) FROM public.enrollments") == 3
    assert scalar("SELECT count(*) FROM public.enrollments_ge") == 1


def test_concurrente_no_supera_cupo_de_electivo():
    results = call_all_at_once([form(n, cupos=5) for n in range(40)])
    assert sum(r["valido"] for r in results) == 5
    assert not any("Error interno" in r["mensaje"] for r in results), results
    assert enrolled(1) == 5


def test_concurrente_no_supera_cupo_fg():
    results = call_all_at_once([form(n, cupos_fg=3) for n in range(40)])
    assert sum(r["valido"] for r in results) == 3
    assert not any("Error interno" in r["mensaje"] for r in results), results
    assert scalar("SELECT count(*) FROM public.enrollments_ge") == 3


def test_concurrente_electivos_cruzados_sin_deadlock():
    variantes = [dict(), dict(e1=ALT1), dict(fg="FG dos"), dict(e1=ALT1, fg="FG dos")]
    forms = [form(n, **variantes[n % 4]) for n in range(40)]
    results = call_all_at_once(forms)
    assert all(r["valido"] for r in results), results


def test_reenvio_igual_es_exito_y_no_duplica():
    assert call(form(1))["mensaje"] == "Inscripción exitosa."
    again = call(form(1))
    assert again == {"valido": True, "mensaje": "Tu inscripción ya estaba registrada."}
    assert scalar("SELECT count(*) FROM public.enrollments") == 3


def test_reenvio_distinto_se_rechaza():
    assert call(form(1))["valido"]
    other = call(form(1, e1=ALT1))
    assert other == {"valido": False, "mensaje": "Ya tienes una inscripción registrada para este año."}
    assert enrolled(4) == 0


def test_bloquea_electivo_del_anio_anterior():
    assert call(form(1, year=YEAR - 1))["valido"]
    result = call(form(1, e1=ALT1))
    assert not result["valido"]
    assert "Ya cursaste" in result["mensaje"]


def test_rechaza_tres_de_la_misma_area():
    result = call(form(1, e2="Área A: Dos en A", e3="Área A: Tres en A"))
    assert not result["valido"]
    assert "misma área" in result["mensaje"]


def test_rechaza_datos_que_no_coinciden():
    args = list(form(1))
    args[1] = "otro@example.invalid"
    assert not call(tuple(args))["valido"]
    assert scalar("SELECT count(*) FROM public.enrollments") == 0


def test_cupo_cuenta_solo_el_mismo_nivel():
    with psycopg.connect(ADMIN_URL) as conn:
        conn.execute(
            'INSERT INTO public.students ("RUN", name, lastname, class_id, email) '
            "VALUES (%s, 'Nombre', 'Ficticio', 3, %s)",
            (clean_run(100), email_of(100)),
        )
    assert call(form(100, curso="3 medio G", cupos=1))["valido"]
    assert call(form(1, cupos=1))["valido"]
    assert not call(form(2, cupos=1))["valido"]


def test_app_no_lee_estudiantes_ni_inscripciones():
    with psycopg.connect(APP_URL) as conn:
        for table in ("students", "enrollments", "enrollments_ge"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(f"SELECT 1 FROM public.{table}")


def test_app_no_escribe_directo():
    with psycopg.connect(APP_URL) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE public.electives SET name = name")


def test_app_lee_el_catalogo():
    with psycopg.connect(APP_URL) as conn:
        assert conn.execute("SELECT count(*) FROM public.electives").fetchone()[0] == 6
