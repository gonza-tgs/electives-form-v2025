import streamlit as st
import re
import httpx
from supabase import create_client, Client
from supabase.client import ClientOptions

# Variables de Entorno
CAPACITY_ELECTIVE = int(st.secrets["CUPOS"])
CAPACITY_ELECTIVE_GE = int(st.secrets["CUPO_FG"])
PROCESS_YEAR = int(st.secrets["PROCESS_YEAR"])

# Supabase API
@st.cache_resource
def get_supabase_client() -> Client:
    APIKEY = st.secrets["SUPABASE_KEY"]
    URL = st.secrets["SUPABASE_URL"]
    client_options = ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
        schema="public",
    )

    return create_client(URL, APIKEY, options=client_options)

supabase: Client = get_supabase_client()

CURSOS_MAP = {
    "2 medio G": 1,
    "2 medio B": 2,
    "3 medio G": 3,
    "3 medio B": 4,
}


def valid_run(run: str) -> bool:
    """Definir una función para validar el RUN chileno

    Args:
        run (str): Un RUN chileno a validar

    Returns:
        bool: True si el RUN es válido, False en caso contrario
    """
    # Mayúsculas
    run = run.upper()

    # Definir la expresión regular para un RUN chileno
    run_regex = r"^\d{7,8}-[\dKk]$"

    # Compilar la expresión regular
    pattern_run = re.compile(run_regex)

    return bool(pattern_run.fullmatch(run))


def same_area_electives(elective_1: str, elective_2: str, elective_3: str) -> bool:
    """Validar que los 3 electivos seleccionados no sean de la misma área

    Args:
        elective_1 (str): Electivo 1 seleccionado
        elective_2 (str): Electivo 2 seleccionado
        elective_3 (str): Electivo 3 seleccionado

    Returns:
        bool: True si los electivos no son los 3 de la misma área, False en caso contrario
    """

    return False if elective_1[:6] == elective_2[:6] == elective_3[:6] else True


@st.cache_data(ttl=3600)
def email_exists(email: str) -> bool:
    """Verificar si el correo electrónico es válido para inscribirse

    Args:
        email (str): Correo electrónico

    Returns:
        bool: True si el correo electrónico es válido, False en caso contrario
    """
    email = email.lower().strip()

    response = (
        supabase.table("students").select("id", "email").eq("email", email).execute()
    )

    return True if len(response.data) > 0 else False


@st.cache_data(ttl=3600)
def valid_user(run: str, email: str, curso: str) -> bool:
    """Verificar si el RUN, email y curso corresponden al usuario

    Args:
        run (str): RUN
        email (str): Correo electrónico
        curso (str): Curso ej.: '2 medio G'

    Returns:
        bool: True si corresponden, False en caso contrario
    """

    run = run.replace("-", "")
    run = run.upper()

    id_curso = CURSOS_MAP.get(curso)

    if not id_curso:
        return False


    response = (
        supabase.table("students")
        .select("id", "class_id, class(id, name, level)")
        .eq("RUN", run)
        .eq("email", email)
        .execute()
    )

    # Respuesta de la DB sobre el usuario
    data = response.data

    # Si coincide RUN e email se verifica que curso correcto
    if len(data) > 0:
        # ID del curso
        response_class = data[0]["class"]
        if id_curso == response_class["id"]:
            return True  # Curso, RUN e email correctos.
        return False  # Curso incorrecto
    return False  # No existe un usuario con los datos proporcionados


def current_student_record(run: str, process_year: int) -> bool:
    """Verificar si el RUN del estudiante ya tiene un registro para el año del proceso.

    Args:
        run (str): RUN del estudiante.
        process_year (int): Año del proceso de inscripción.

    Returns:
        bool: True si ya se encuentra registrado, False en caso contrario.
    """
    run = run.replace("-", "")
    run = run.upper()

    response = (
        supabase.table("enrollments")
        .select("student_run", "process_year")
        .eq("student_run", run)
        .eq("process_year", process_year)
        .execute()
    )

    return True if len(response.data) > 0 else False


def elective_availability(
    elective: str,
    process_year: int = PROCESS_YEAR,
    elective_capacity: int = CAPACITY_ELECTIVE,
) -> bool:
    """Verificar que hay cupos disponibles para el electivo.

    Args:
        elective (str): Nombre del electivo a verificar.
        process_year (int): Año del proceso para filtrar las inscripciones.
        elective_capacity (int): Capacidad máxima de cupos para el electivo.

    Returns:
        bool: True si hay cupos disponibles, False en caso contrario.
    """

    # ID del electivo
    elective = elective[8:] # Quitar área a la que pertence el electivo
    elective_response = (
        supabase.table("electives").select("id").eq("name", elective).execute()
    )

    if not elective_response.data:
        return False
    elective_id = elective_response.data[0]["id"]

    # Info electivo seleccionado
    response = (
        supabase.table("enrollments")
        .select("elective_id")
        .eq("elective_id", elective_id)
        .eq("process_year", process_year)
        .execute()
    )
    current_enrollment = len(response.data)

    return True if current_enrollment <= elective_capacity else False


def ge_elective_availability(
    elective_ge: str, curso: str, capacity_elective_ge: int = CAPACITY_ELECTIVE_GE
) -> bool:
    """Verificar que hay cupos disponibles para el electivo de formación general

    Args:
        elective_ge (str): Electivo de Formación General
        curso (str): Curso del estudiante
        capacity_elective_ge (int): Número de cupos disponibles para el electivo

    Returns:
        bool: True si hay cupos disponibles, False en caso contrario
    """
    # ID del curso
    id_curso = CURSOS_MAP.get(curso)
    if not id_curso:
        return False

    # ID del electivo
    elective_response = (
        supabase.table("general_edu").select("id").eq("name", elective_ge).execute()
    )

    if not elective_response.data:
        return False
    elective_id = elective_response.data[0]["id"]

    # Info del electivo
    response = (
        supabase.table("enrollments_ge")
        .select("id")
        .eq("id", elective_id)
        .eq("class_id", id_curso)
        .execute()
    )
    current_enrollment = len(response.data)

    return True if current_enrollment <= capacity_elective_ge else False


@st.cache_data(ttl=3600)
def student_enrolled_in_previous_elective(
    run: str, elective: str, current_process_year: int = PROCESS_YEAR
) -> bool:
    """Verificar si el estudiante está inscrito en el mismo electivo del año anterior.

    Args:
        run (str): RUN del estudiante.
        elective (str): Nombre del electivo a verificar.
        current_process_year (int): Año del proceso de inscripción actual.

    Returns:
        bool: True si ya cursó el electivo, False en caso contrario.
    """

    # Año de proceso anterior
    previous_process_year = current_process_year - 1

    run = run.replace("-", "")
    run = run.upper()

    # ID del electivo
    elective = elective[8:] # Quitar área a la que pertence el electivo
    elective_response = (
        supabase.table("electives").select("id").eq("name", elective).execute()
    )

    if not elective_response.data:
        return False
    elective_id = elective_response.data[0]["id"]

    # Coincidencia de electivo previamente realizado
    response = (
        supabase.table("enrollments")
        .select("student_run")
        .eq("student_run", run)
        .eq("process_year", previous_process_year)
        .eq("elective_id", elective_id)
        .execute()
    )

    return True if len(response.data) > 0 else False


def insert_user_record(
    student_run: str,
    elective_1: str,
    elective_2: str,
    elective_3: str,
    elective_ge: str,
    curso: str,
    process_year: int = PROCESS_YEAR,
) -> bool:
    """Insertar registro en la base de datos de inscripciones.

    Args:
        student_run (str): RUN del estudiante.
        elective_1 (str): Nombre del primer electivo.
        elective_2 (str): Nombre del segundo electivo.
        elective_3 (str): Nombre del tercer electivo.
        elective_ge (str): Nombre del electivo de formación general.
        curso (str): Curso del estudiante.
        process_year (int): Año del proceso de inscripción.

    Returns:
        bool: True si se insertó correctamente, False en caso contrario.
    """
    # Formato RUN
    student_run = student_run.replace("-", "")

    # ID del curso indicado
    id_curso = CURSOS_MAP.get(curso)
    if not id_curso:
        return False

    # ID electivos
    elective_1 = elective_1[8:] # Quitar área a la que pertence el electivo
    elective_2 = elective_2[8:] # Quitar área a la que pertence el electivo
    elective_3 = elective_3[8:] # Quitar área a la que pertence el electivo

    electives_response = (
        supabase.table("electives")
        .select("id")
        .in_("name", [elective_1, elective_2, elective_3])
        .execute()
    )

    if len(electives_response.data) != 3:
        return False
    elective_1_id = electives_response.data[0]["id"]
    elective_2_id = electives_response.data[1]["id"]
    elective_3_id = electives_response.data[2]["id"]

    # Insertar registro en la base de datos de inscripciones
    response_electives = (
        supabase.table("enrollments")
        .insert(
            [
                {
                    "student_run": student_run,
                    "elective_id": elective_1_id,
                    "process_year": process_year,
                    "class_id": id_curso,
                },
                {
                    "student_run": student_run,
                    "elective_id": elective_2_id,
                    "process_year": process_year,
                    "class_id": id_curso,
                },
                {
                    "student_run": student_run,
                    "elective_id": elective_3_id,
                    "process_year": process_year,
                    "class_id": id_curso,
                },
            ]
        )
        .execute()
    )
    electives_ge = {
        "Historia, Geografía y Cs. Sociales": 1,
        "Educación Musical": 2,
        "Educación Física y Salud": 3,
        "Artes Visuales": 4
    }

    elective_ge_id = electives_ge.get(elective_ge)

    if not elective_ge_id:
        return False

    response_ge = (
        supabase.table("enrollments_ge")
        .insert(
            [
                {
                    "elective_id": elective_ge_id,
                    "process_year": process_year,
                    "class_id": id_curso,
                    "student_run": student_run,
                }
            ]
        )
        .execute()
    )

    return True if response_electives and response_ge else False


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
    """Verificar que no existan campos vacíos

    Keyword arguments:
    argument -- Todas las respuestas del formulario
    Return: True si hay campos vacíos, False en caso contrario
    """

    answers = [run, email, name, class_name, elective_1, elective_2, elective_3, elective_ge]
    empty_answers = [True for answer in answers if answer is None or answer == ""]

    return True if any(empty_answers) else False


def validate_form(
    run: str,
    email: str,
    class_name: str,
    elective_1: str,
    elective_2: str,
    elective_3: str,
    elective_ge: str,
    process_year: int
):
    """Ejecuta una serie de validaciones sobre los datos de un formulario.

    Esta función orquesta todas las validaciones individuales (RUN, email, cupos, etc.)
    y muestra un mensaje de error apropiado si alguna de ellas falla.

    Args:
        run (str): RUN del estudiante.
        email (str): Email del estudiante.
        class_name (str): Nombre del curso del estudiante.
        elective_1 (str): Nombre del primer electivo.
        elective_2 (str): Nombre del segundo electivo.
        elective_3 (str): Nombre del tercer electivo.
        elective_ge (str): Nombre del electivo de formación general.
        process_year (int): Año del proceso de inscripción.

    Returns:
        bool: True si todas las validaciones son exitosas, False en caso contrario.
    """
    # Verif icar si el RUN es válido
    if run and not valid_run(run):
        st.error("El RUN ingresado no es válido.")
        return False

    # Verificar si el email es válido y si existe en la base de datos
    if email and not email_exists(email):
        st.error("El correo ingresado no es válido. Por favor ingresa tu correo institucional correctamente.")
        return False

    # Verificar que los electivos no sean de la misma área
    if not same_area_electives(elective_1, elective_2, elective_3):
        st.error("No se puede inscribir 3 electivos de la misma área.")
        return False

    # Verificar los datos del usuario
    if not valid_user(run, email, class_name):
        st.error("La información ingresada no es válida. Verifica que coincida RUN, correo institucional y el curso.")
        return False

    # Verificar que no se haya inscrito en el proceso actual
    if current_student_record(run, process_year):
        st.error(f"El estudiante ingresado ya inscribió sus electivos para el proceso actual, año {process_year}.")
        return False

    # Verificar disponibilidad del electivo 1
    if not elective_availability(elective_1, PROCESS_YEAR, CAPACITY_ELECTIVE):
        st.error("Electivo 1 sin cupos disponibles.")
        return False

    # Verificar disponibilidad del electivo 2
    if not elective_availability(elective_2, PROCESS_YEAR, CAPACITY_ELECTIVE):
        st.error("Electivo 2 sin cupos disponibles.")
        return False

    # Verificar disponibilidad del electivo 3
    if not elective_availability(elective_3, PROCESS_YEAR, CAPACITY_ELECTIVE):
        st.error("Electivo 3 sin cupos disponibles.")
        return False

    # Verificar disponibilidad del electivo de formación general para el curso indicado
    if not ge_elective_availability(elective_ge, class_name, CAPACITY_ELECTIVE_GE):
        st.error("Electivo de Formacion General sin cupos disponibles.")
        return False

    # Verificar que el estudiante no haya inscrito el mismo electivo el año anterior
    if student_enrolled_in_previous_elective(run, elective_1, process_year):
        st.error(f"El electivo {elective_1} ya fue inscrito en el proceso {process_year-1}.")
        return False

    # Verificar que el estudiante no haya inscrito el mismo electivo el año anterior
    if student_enrolled_in_previous_elective(run, elective_2, process_year):
        st.error(f"El electivo {elective_2} ya fue inscrito en el proceso {process_year-1}.")
        return False

    # Verificar que el estudiante no haya inscrito el mismo electivo el año anterior
    if student_enrolled_in_previous_elective(run, elective_3, process_year):
        st.error(f"El electivo {elective_3} ya fue inscrito en el proceso {process_year-1}.")
        return False

    return True