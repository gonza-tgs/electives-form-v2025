import logging
import re

import streamlit as st
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

# --- Cargar variables de entorno ---
CAPACITY_ELECTIVE = int(st.secrets["CUPOS"])
CAPACITY_ELECTIVE_GE = int(st.secrets["CUPO_FG"])
PROCESS_YEAR = int(st.secrets["PROCESS_YEAR"])

INSCRIBIR_SQL = """
    SELECT public.validar_e_inscribir_electivos(
        p_run => %(p_run)s,
        p_email => %(p_email)s,
        p_curso_nombre => %(p_curso_nombre)s,
        p_electivo_1_full => %(p_electivo_1_full)s,
        p_electivo_2_full => %(p_electivo_2_full)s,
        p_electivo_3_full => %(p_electivo_3_full)s,
        p_electivo_fg_nombre => %(p_electivo_fg_nombre)s,
        p_process_year => %(p_process_year)s,
        p_cupos_electivo => %(p_cupos_electivo)s,
        p_cupos_fg => %(p_cupos_fg)s
    )
"""

# --- Conexión a Postgres ---
@st.cache_resource
def get_pool() -> ConnectionPool:
    return ConnectionPool(
        st.secrets["DATABASE_URL"],
        min_size=1,
        max_size=10,
        timeout=15,
        check=ConnectionPool.check_connection,
        open=True,
        kwargs={"options": "-c statement_timeout=15000"},
    )

# --- Validaciones "Ligeras" (no usan la red) ---

def valid_run(run: str) -> bool:
    """Valida el formato del RUN (sin DB)."""
    run = run.upper()
    run_regex = r"^\d{7,8}-[\dKk]$"
    pattern_run = re.compile(run_regex)
    return bool(pattern_run.fullmatch(run))

def empty_form(
        run: str,
        email: str,
        name: str,
        class_name: str,
        elective_1: str,
        elective_2: str,
        elective_3: str,
        elective_ge: str
    ) -> bool:
    """Verificar que no existan campos vacíos (sin DB)."""
    answers = [run, email, name, class_name, elective_1, elective_2, elective_3, elective_ge]
    # 'None' y 'str' vacíos son problemáticos para st.radio, verificamos ambos
    empty_answers = [ans is None or str(ans).strip() == "" or str(ans) == "None" for ans in answers]
    return any(empty_answers)

# --- Función Principal ---

def validate_and_insert_form(
    run: str,
    email: str,
    class_name: str,
    elective_1: str,
    elective_2: str,
    elective_3: str,
    elective_ge: str,
):
    """
    Ejecuta validación E inserción en la DB usando UNA SOLA llamada a la función SQL.
    """

    # 1. Validaciones ligeras primero
    if not valid_run(run):
        st.error("El RUN ingresado no tiene un formato válido.")
        return False

    # 2. Agrupar todos los parámetros para la función SQL
    params = {
        "p_run": run,
        "p_email": email,
        "p_curso_nombre": class_name,
        "p_electivo_1_full": elective_1,
        "p_electivo_2_full": elective_2,
        "p_electivo_3_full": elective_3,
        "p_electivo_fg_nombre": elective_ge,
        "p_process_year": PROCESS_YEAR,
        "p_cupos_electivo": CAPACITY_ELECTIVE,
        "p_cupos_fg": CAPACITY_ELECTIVE_GE
    }

    try:
        # 3. Llamar la función. El bloque confirma la transacción al salir,
        #    lo que también libera los bloqueos tomados por la función.
        with get_pool().connection() as conn:
            result = conn.execute(INSCRIBIR_SQL, params).fetchone()[0]

        # 4. Interpretar la respuesta del JSON
        if result["valido"]:
            return True # ¡Éxito! La validación pasó Y los datos se insertaron.
        else:
            # Si no es válido, mostrar el mensaje de error exacto de la DB
            st.error(result["mensaje"])
            return False

    except Exception:
        # El detalle queda en los logs: puede incluir datos de la conexión.
        logger.exception("Error al inscribir electivos")
        st.error("Error de conexión con la base de datos. Intenta de nuevo.")
        return False
