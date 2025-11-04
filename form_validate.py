import streamlit as st
import re
from supabase import create_client, Client
from supabase.client import ClientOptions

# --- Cargar variables de entorno ---
CAPACITY_ELECTIVE = int(st.secrets["CUPOS"])
CAPACITY_ELECTIVE_GE = int(st.secrets["CUPO_FG"])
PROCESS_YEAR = int(st.secrets["PROCESS_YEAR"])

# --- Conexión a Supabase (igual que antes) ---
@st.cache_resource
def get_supabase_client() -> Client:
    APIKEY = st.secrets["SUPABASE_KEY"]
    URL = st.secrets["SUPABASE_URL"]
    client_options = ClientOptions(
        postgrest_client_timeout=15, # Puedes mantener o subir este timeout
        storage_client_timeout=15,
        schema="public",
    )
    return create_client(URL, APIKEY, options=client_options)

supabase: Client = get_supabase_client()

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

# --- Función Principal (RPC) ---

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
    Ejecuta validación E inserción en la DB usando UNA SOLA llamada RPC.
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
        # 3. Llamar la función RPC
        # ¡Esta es la ÚNICA llamada a la base de datos!
        response = supabase.rpc("validar_e_inscribir_electivos", params).execute()
        
        # 4. Interpretar la respuesta del JSON
        result = response.data
        
        if result["valido"]:
            return True # ¡Éxito! La validación pasó Y los datos se insertaron.
        else:
            # Si no es válido, mostrar el mensaje de error exacto de la DB
            st.error(result["mensaje"])
            return False

    except Exception as e:
        # Capturar errores de red (como el 502)
        st.error(f"Error de conexión con la base de datos. Intenta de nuevo. (Detalle: {e})")
        return False