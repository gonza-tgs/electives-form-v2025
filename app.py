# Importat librerías
import streamlit as st
import time  # Necesario para la simulación de tiempo de respuesta
import smtplib  # Para enviar correos
import ssl  # Para conexión segura
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage  # Para construir el correo
from form_validate import validate_and_insert_form, empty_form
from load_electives import get_electives

# --- Inicializar el Estado de Sesión ---
# 'is_submitting' (booleano): Controla el atributo 'disabled' del botón.
if "is_submitting" not in st.session_state:
    st.session_state.is_submitting = False
# 'form_submitted' (booleano): Indica si el formulario ya fue procesado con éxito.
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False

# Cargar variables de entorno
LEVEL = st.secrets["LEVEL"]
CURSOS = (
    st.secrets["CURSOS"][:2] if LEVEL == "enabled_3medio" else st.secrets["CURSOS"][2:]
)
ELECTIVOS_FG = (
    st.secrets["ELECTIVOS_FG"][:2]
    if LEVEL == "enabled_3medio"
    else st.secrets["ELECTIVOS_FG"][2:]
)
ELECTIVO_1, ELECTIVO_2, ELECTIVO_3 = get_electives(LEVEL)
PROCESS_YEAR = int(st.secrets["PROCESS_YEAR"])

CAPACITY_ELECTIVE = int(st.secrets["CUPOS"])
CAPACITY_ELECTIVE_GE = int(st.secrets["CUPO_FG"])


# --- Función de Callback para Deshabilitar el Botón ---
def handle_submission():
    """Esta función se ejecuta al hacer clic y solo marca el inicio del procesamiento."""
    # 1. Deshabilitar el botón INMEDIATAMENTE al hacer clic
    st.session_state.is_submitting = True


def send_confirmation_email(
    name, run, email, curso, electivo_1, electivo_2, electivo_3, electivo_fg, year, timestamp_str
):
    """
    Construye y envía un correo de confirmación al estudiante.
    """
    try:
        # --- Cargar credenciales ---
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]
        smtp_server = st.secrets["SMTP_SERVER"]
        smtp_port = int(st.secrets["SMTP_PORT"])

        # --- Construir el mensaje ---
        msg = EmailMessage()
        msg["Subject"] = f"Confirmación de Inscripción de Electivos {year}"
        msg["From"] = sender_email
        msg["To"] = email

        # --- Crear cuerpo HTML del correo ---
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ width: 90%; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                h2 {{ color: #333; }}
                ul {{ list-style-type: none; padding-left: 0; }}
                li {{ margin-bottom: 10px; }}
                li strong {{ color: #555; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Hola {name},</h2>
                <p>Hemos recibido exitosamente tu inscripción para los electivos del proceso {year}.</p>
                <p>A continuación, te dejamos un resumen de tus selecciones:</p>
                <ul>
                    <li><strong>Nombre:</strong> {name}</li>
                    <li><strong>RUN:</strong> {run}</li>
                    <li><strong>Curso:</strong> {curso}</li>
                    <li><strong>Electivo 1:</strong> {electivo_1}</li>
                    <li><strong>Electivo 2:</strong> {electivo_2}</li>
                    <li><strong>Electivo 3:</strong> {electivo_3}</li>
                    <li><strong>Electivo Formación General:</strong> {electivo_fg}</li>

                    <li style="color: #444;"><strong>Fecha y Hora de Inscripción:</strong> {timestamp_str}</li>
                </ul>
                <p>Por favor, guarda este correo como comprobante de tu inscripción.</p>
                <p>Saludos,<br>Equipo de Coordinación Académica TGS</p>
            </div>
        </body>
        </html>
        """

        # Añadir el cuerpo HTML
        msg.set_content(
            "Este es un correo de confirmación. Por favor, habilita la vista HTML para ver el resumen."
        )
        msg.add_alternative(body, subtype="html")

        # --- Enviar el correo ---
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)  # Iniciar conexión segura
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return True  # Devuelve True si el envío fue exitoso

    except Exception as e:
        # En caso de error, lo mostramos en la consola de Streamlit
        print(f"Error al enviar el correo: {e}")
        return False  # Devuelve False si hubo un error

# -------------------------------------------------------------
# ----------------- TÍTULO DE LA APLICACIÓN -------------------
# -------------------------------------------------------------
st.image("./SOY_GARDEN.png")
st.title(f"Formulario de Inscripción de electivos - {PROCESS_YEAR}")
st.divider()
st.text("Recuerda que debes seguir las reglas para inscribirte correctamente.")

# Identificación del estudiante
# El formulario debe ser dibujado en cada re-ejecución
with st.form(key="form"):

    # --- Student Identification Section ---
    # --- Sección de identificación del estudiante ---
    st.header("Identificación de Estudiante")

    # Nombre
    name = st.text_input("Ingresa tu nombre completo:", placeholder="Nombre Completo")
    st.caption("Ejemplo: Francisca Alejandra Pérez Ortiz")

    # RUN
    run = st.text_input("Ingresa tu RUN:", placeholder="12345678-k")
    st.caption(
        "Debes ingresar tu run sin puntos, con guión y dígito verificador. Ej.: 11222333-X"
    )

    # Email
    email = st.text_input(
        "Ingresa tu correo institucional:",
        placeholder="nombre.apellido@estudiantes.colegiotgs.cl",
    )
    st.caption("Ejemplo: francisca.perez@estudiantes.colegiotgs.cl")

    # Curso
    curso = str(st.radio(f"Selecciona tu curso actual (año {PROCESS_YEAR-1}):", CURSOS, index=None))

    # --- Differentiated Training Enrollment Section ---
    # --- Sección de inscripción Formación Diferenciada ---
    st.divider()

    # Select differentiated training electives
    # Seleccionar los electivos de formación diferenciada
    st.header("Electivos de Formación Diferenciada")

    # Electivo 1
    electivo_1 = str(
        st.radio(
            "Selecciona el Electivo 1",
            ELECTIVO_1,
            index=None,
        )
    )

    # Electivo 2
    electivo_2 = str(
        st.radio(
            "Selecciona el Electivo 2",
            ELECTIVO_2,
            index=None,
        )
    )

    # Electivo 3
    electivo_3 = str(
        st.radio(
            "Selecciona el Electivo 3",
            ELECTIVO_3,
            index=None,
        )
    )

    st.divider()

    # General Training Electives
    # Electivos de Formación General
    st.header("Electivos de Formación General")

    electivo_fg = str(
        st.radio(
            "Selecciona tu Electivo de Formación General",
            ELECTIVOS_FG,
            index=None,
        )
    )

    # Botón de envío. Usa el estado de sesión para deshabilitarse.
    submit_button = st.form_submit_button(
        label="Submit",
        on_click=handle_submission,  # Ejecuta la función que deshabilita
        disabled=st.session_state.is_submitting or st.session_state.form_submitted,
    )

# --- Lógica de Procesamiento y Bloqueo ---

# Si is_submitting es True, significa que el botón fue presionado y ahora procesamos.
if st.session_state.is_submitting and not st.session_state.form_submitted:

    # Mostrar un spinner para indicar al usuario que algo está pasando
    with st.spinner("Procesando inscripción..."):

        if empty_form(
            run, email, name, curso, electivo_1, electivo_2, electivo_3, electivo_fg
        ):
            st.error(
                "Debes llenar todos los campos para continuar. El formulario se reiniciará en 2 segundos."
            )
            # 4. Habilitar el botón de nuevo para que el usuario pueda corregir y reintentar
            st.session_state.is_submitting = False
            time.sleep(2)
            st.rerun()
        else:
            # Esta ÚNICA función ahora valida E inserta los datos
            success = validate_and_insert_form(
                run,
                email,
                curso,
                electivo_1,
                electivo_2,
                electivo_3,
                electivo_fg,
            )

            if not success:
                # La validación falló. El error ya fue mostrado por st.error() dentro de la función.
                st.warning("El formulario se reiniciará para que puedas corregir.")
                # Habilitar el botón de nuevo para que el usuario pueda corregir
                st.session_state.is_submitting = False
                time.sleep(5) 
                st.rerun()
            else:
                # ¡ÉXITO! La validación pasó y los datos ya se insertaron.
                # 1. Marcar como exitoso
                st.session_state.form_submitted = True

                # ******************************************************
                # ** 2. INTENTAR ENVIAR EL CORREO DE CONFIRMACIÓN **
                # ******************************************************
                # ---> 1. Genera la marca de tiempo AHORA <---
                # (Usará la hora de Santiago de Chile)
                tz = ZoneInfo("America/Santiago")
                now = datetime.now(tz=tz)
                # Formato: 03-11-2025 21:58:30 (Día-Mes-Año Hora:Min:Seg)
                # Le añadimos (UTC) para que el usuario sepa la zona horaria
                timestamp_string = now.strftime("%d-%m-%Y %H:%M:%S")
                email_sent = send_confirmation_email(
                    name,
                    run,
                    email,
                    curso,
                    electivo_1,
                    electivo_2,
                    electivo_3,
                    electivo_fg,
                    PROCESS_YEAR,
                    timestamp_string
                )

                if email_sent:
                    st.session_state.email_status = "enviado"
                else:
                    st.session_state.email_status = "fallido"

                # 2. Deshabilitar el estado de envío (aunque form_submitted ya lo bloquea)
                st.session_state.is_submitting = False

                # 3. Forzar una re-ejecución para mostrar el resultado y el botón deshabilitado final
                st.rerun()

# --- Mostrar Resultado Final ---
if st.session_state.form_submitted:
    # Este mensaje solo aparece después de que el proceso fue exitoso
    st.success("¡Inscripción exitosa! Tus respuestas han sido guardadas.")

    # Informar sobre el estado del correo
    if st.session_state.email_status == "enviado":
        st.info(f"Se ha enviado una copia de tu inscripción a tu correo: {email}")
    elif st.session_state.email_status == "fallido":
        st.warning(
            "No pudimos enviar el correo de confirmación. "
            "Por favor, toma una captura de pantalla de esta página como comprobante."
        )


    # El botón permanece deshabilitado ya que st.session_state.form_submitted es True
