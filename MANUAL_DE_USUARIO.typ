#set page(
  paper: "a4",
  margin: (top: 1.8cm, bottom: 1.8cm, left: 1.8cm, right: 1.8cm),
  header: context {
    let page-num = here().page()
    if page-num > 1 {
      text(size: 8pt, fill: rgb("#6b7280"), font: ("Roboto", "Noto Sans", "DejaVu Sans"))[
        #grid(
          columns: (1fr, auto),
          align: (left, right),
          [Colegio Talagante Garden School | *Inscripción de Electivos*],
          [Manual de Usuario]
        )
        #v(-4pt)
        #line(length: 100%, stroke: 0.5pt + rgb("#d1d5db"))
      ]
    }
  },
  footer: context {
    let page-num = here().page()
    let total-pages = counter(page).final().at(0)
    text(size: 8pt, fill: rgb("#6b7280"), font: ("Roboto", "Noto Sans", "DejaVu Sans"))[
      #line(length: 100%, stroke: 0.5pt + rgb("#d1d5db"))
      #v(-2pt)
      #grid(
        columns: (1fr, auto),
        align: (left, right),
        [Unidad de Informática - admin\@colegiotgs.cl | ba.calderon\@colegiotgs.cl],
        [Página #page-num de #total-pages]
      )
    ]
  }
)

#set text(
  font: ("Roboto", "Noto Sans", "DejaVu Sans"),
  size: 9pt,
  lang: "es",
  fill: rgb("#1f2937"),
  spacing: 120%
)

#set par(
  justify: true,
  leading: 0.55em
)

#show heading: it => [
  #set text(fill: rgb("#0f2f57"), weight: "bold")
  #v(0.3em)
  #it
  #v(0.15em)
]

#show heading.where(level: 1): it => [
  #set text(size: 11.8pt, fill: rgb("#0f2f57"))
  #v(0.35em)
  #it
  #v(0.15em)
  #line(length: 100%, stroke: 1.2pt + rgb("#1e40af"))
  #v(0.15em)
]

#show heading.where(level: 2): it => [
  #set text(size: 9.8pt, fill: rgb("#1e3a8a"))
  #v(0.28em)
  #it
  #v(0.1em)
]

#show heading.where(level: 3): it => [
  #set text(size: 9pt, fill: rgb("#1e40af"))
  #v(0.2em)
  #it
  #v(0.08em)
]

#let callout(title: "", color: rgb("#2563eb"), bg: rgb("#eff6ff"), body) = {
  rect(
    width: 100%,
    fill: bg,
    stroke: (left: 3pt + color, rest: 0.5pt + color.lighten(60%)),
    radius: (right: 4pt),
    inset: (x: 7.5pt, y: 5pt),
    outset: 0pt,
    [
      #if title != "" [
        #text(weight: "bold", fill: color, size: 8.2pt)[#title]
        #v(1.2pt)
      ]
      #text(size: 8.2pt, fill: rgb("#1f2937"))[#body]
    ]
  )
}

#let rule-box(title: "", body) = callout(title: title, color: rgb("#1e40af"), bg: rgb("#eff6ff"), body)
#let alert-box(body) = callout(title: "ATENCIÓN / REGLA DEL SISTEMA", color: rgb("#b91c1c"), bg: rgb("#fef2f2"), body)
#let success-box(body) = callout(title: "COMPROBANTE", color: rgb("#15803d"), bg: rgb("#f0fdf4"), body)

// --- PÁGINA 1: PORTADA, INTRODUCCIÓN, REQUISITOS Y VISTA GLOBAL ---
#align(center)[
  #image("SOY_GARDEN.png", width: 32%)
  #v(2pt)
  #text(size: 16pt, weight: "bold", fill: rgb("#0f2f57"))[MANUAL DE USUARIO] \
  #text(size: 11pt, weight: "medium", fill: rgb("#374151"))[Formulario de Inscripción de Electivos] \
  #text(size: 8pt, fill: rgb("#6b7280"))[Colegio Talagante Garden School | Proceso de Postulación Académica]
  #v(2pt)
  #line(length: 50%, stroke: 1.2pt + rgb("#0f2f57"))
]

#v(2pt)

#grid(
  columns: (1.25fr, 0.75fr),
  gutter: 14pt,
  align: (top, top),
  [
    = 1. Introducción y Objetivo
    Bienvenido/a al *Manual de Usuario del Formulario de Inscripción de Electivos*. Esta plataforma permite a los y las estudiantes del *Colegio Talagante Garden School* postular a sus asignaturas de *Formación Diferenciada* y *Formación General* de manera autónoma, transparente, rápida y segura.

    *Características principales del sistema:*
    - Validación de antecedentes y formato de RUN en tiempo real.
    - Aplicación estricta de las reglas académicas ministeriales e internas.
    - Control automático de cupos por electivo en el servidor.
    - Bloqueo preventivo de envíos dobles o accidentales.
    - Comprobante inmediato emitido al correo institucional.

    #v(3pt)
    = 2. Requisitos Previos
    Antes de completar el formulario, asegúrate de contar con:
    + *Correo institucional:* Cuenta oficial `@estudiantes.colegiotgs.cl`.
    + *Cédula de Identidad (RUN):* RUN completo con guión y dígito verificador (ej: `12345678-k` o `11222333-9`).
    + *Preferencias informadas:* Haber revisado la oferta electiva de tu nivel y las combinaciones permitidas.
    + *Dispositivo con Internet:* Computador o smartphone con navegador web actualizado.
  ],
  [
    #align(center)[
      #image("img/01_inicio_formulario.png", height: 16.5cm, fit: "contain")
      #v(-4pt)
      #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 1: Vista general del formulario.]
    ]
  ]
)

#pagebreak()

// --- PÁGINA 2: PASO A PASO Y REGLAS DE INSCRIPCIÓN ---
= 3. Guía Paso a Paso para la Inscripción

A continuación se detalla cómo completar cada sección del formulario:

== Paso 1: Identificación del Estudiante
#grid(
  columns: (1.1fr, 0.9fr),
  gutter: 12pt,
  align: (top, top),
  [
    Registra tus datos personales y curso:
    + *Nombre Completo:* Tal como figura en tu registro escolar (ej: _Francisca Alejandra Pérez Ortiz_).
    + *RUN:* Sin puntos, con guión y dígito verificador (ej: `12345678-k`).
    + *Correo Institucional:* Casilla oficial `@estudiantes.colegiotgs.cl`.
    + *Curso Actual:* Tu curso del año en curso (ej: _3 medio G_ o _3 medio B_).
  ],
  [
    #align(center)[
      #image("img/02_identificacion_estudiante.png", width: 100%)
      #v(-4pt)
      #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 2: Identificación de Estudiante.]
    ]
  ]
)

== Paso 2: Selección de Electivos de Formación Diferenciada y Reglas

#grid(
  columns: (1.15fr, 0.85fr),
  gutter: 12pt,
  align: (top, top),
  [
    Escoge una asignatura por cada bloque diferenciado (Electivos 1, 2 y 3) pertenecientes a las áreas formativas:
    - *Área A:* Humanidades / Filosofía / Lenguaje / Historia.
    - *Área B:* Ciencias (Biología, Física, Química) / Matemática.
    - *Área C:* Artes / Educación Física y Salud / Música.

    #v(2pt)
    #rule-box(title: "REGLAS OBLIGATORIAS DE INSCRIPCIÓN")[
      + *Diversidad de Áreas:* *No se permite inscribir 3 electivos de la misma área*. Tus 3 elecciones deben pertenecer al menos a *2 áreas distintas* (ejemplo: 2 de Área B y 1 de Área A).
      + *No Repetición:* Si pasas a *4° Medio*, no puedes seleccionar un electivo ya cursado en *3° Medio*.
      + *Cupos Limitados:* Las vacantes se asignan por orden de envío.
      + *Selección Única:* Exactamente 1 asignatura por bloque.
    ]
  ],
  [
    #align(center)[
      #image("img/03_electivos_diferenciada.png", width: 100%)
      #v(-4pt)
      #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 3: Electivos Diferenciados 1, 2 y 3.]
    ]
  ]
)

== Paso 3: Selección de Formación General y Envío
#grid(
  columns: (1.1fr, 0.9fr),
  gutter: 12pt,
  align: (top, top),
  [
    + *Electivo Formación General:* Marca tu asignatura común de preferencia (ej: _Educación Física y Salud_ o _Artes Visuales_).
    + *Botón Submit:* Haz clic en *Submit*. El botón se desactivará de inmediato para prevenir envíos duplicados mientras el servidor procesa tu inscripción.
  ],
  [
    #align(center)[
      #image("img/04_electivos_formacion_general.png", width: 100%)
      #v(-4pt)
      #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 4: Formación General y Envío.]
    ]
  ]
)

#pagebreak()

// --- PÁGINA 3: VALIDACIONES Y COMPROBANTES ---
= 4. Validaciones y Control del Sistema

El sistema procesa y valida automáticamente la solicitud en el servidor:

#grid(
  columns: (1.1fr, 0.9fr),
  gutter: 12pt,
  align: (top, top),
  [
    - *Campos Incompletos:* Si falta algún dato, se notificará y el formulario se reiniciará en 2 segundos.
    - *Formato de RUN:* Se rechaza cualquier formato sin guión o con caracteres incorrectos.
    - *Validación de Áreas y Repetición:* Si marcas 3 asignaturas de una sola área o un electivo ya cursado en 3° Medio, el sistema denegará la inscripción.
    - *Inscripción Previa:* Solo se permite una inscripción por RUN por año académico.
    - *Cupos Disponibles:* Si un electivo se llena, se informará para elegir otra opción del bloque.
  ],
  [
    #align(center)[
      #image("img/07_alerta_error.png", width: 100%)
      #v(-4pt)
      #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 5: Alerta de validación o postulación previa.]
    ]
  ]
)

#v(3pt)
= 5. Confirmación y Comprobante Oficial

Al procesar exitosamente la inscripción, se entregan dos respaldos oficiales:

== 1. Confirmación en Pantalla
Se desplegará una notificación verde que certifica el guardado de los datos y el despacho del comprobante:
#align(center)[
  #image("img/05_confirmacion_exitosa.png", width: 85%)
  #v(-4pt)
  #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 6: Notificación de confirmación exitosa en pantalla.]
]

== 2. Comprobante por Correo Institucional
Llegará a tu bandeja de entrada un correo con el resumen de tus electivos y la *marca temporal con hora oficial de Santiago de Chile*:

#grid(
  columns: (1.1fr, 0.9fr),
  gutter: 12pt,
  align: (top, top),
  [
    #success-box[
      *Conserva este correo:* Constituye tu comprobante oficial de fecha y hora exacta de inscripción.
    ]
    #v(2pt)
    - Si no aparece en tu bandeja principal, revisa la carpeta *Spam*.
    - La confirmación verde en pantalla asegura que tus datos ya están almacenados en el servidor.
  ],
  [
    #align(center)[
      #image("img/06_correo_respaldo.png", width: 95%)
      #v(-4pt)
      #text(size: 7.5pt, fill: rgb("#6b7280"), style: "italic")[Figura 7: Respaldo emitido al correo del estudiante.]
    ]
  ]
)

#pagebreak()

// --- PÁGINA 4: FAQ, TROUBLESHOOTING Y CONTACTO ---
= 6. Preguntas Frecuentes (FAQ)

#callout(title: "¿Por qué no puedo elegir 3 electivos de la misma área?", color: rgb("#374151"), bg: rgb("#f9fafb"))[
  Por normativa ministerial y del colegio, se exige que las elecciones cubran al menos 2 áreas del conocimiento diferentes para asegurar una formación equilibrada.
]

#v(2pt)
#callout(title: "¿Puedo modificar mi inscripción una vez enviada?", color: rgb("#374151"), bg: rgb("#f9fafb"))[
  No desde la web. Para resguardar el orden de prelación y cupos en tiempo real, el sistema bloquea nuevas postulaciones para un RUN ya registrado. Para solicitudes excepcionales, contacta a la Unidad de Informática.
]

#v(3pt)
= 7. Problemas Frecuentes y Soluciones

#table(
  columns: (1.1fr, 1.2fr, 1.7fr),
  stroke: 0.5pt + rgb("#d1d5db"),
  fill: (col, row) => if row == 0 { rgb("#eff6ff") } else if calc.odd(row) { rgb("#f9fafb") } else { white },
  inset: (x: 5pt, y: 4pt),
  align: (left, left, left),
  [#text(weight: "bold", size: 7.8pt, fill: rgb("#0f2f57"))[Mensaje / Problema]],
  [#text(weight: "bold", size: 7.8pt, fill: rgb("#0f2f57"))[Causa Común]],
  [#text(weight: "bold", size: 7.8pt, fill: rgb("#0f2f57"))[Solución Paso a Paso]],
  
  [#text(size: 7.5pt, weight: "bold")[RUN no válido]],
  [#text(size: 7.5pt)[Escrito con puntos o sin guión / dígito verificador.]],
  [#text(size: 7.5pt)[Escribirlo sin puntos y con guión: `12345678-k` o `11222333-9`.]],

  [#text(size: 7.5pt, weight: "bold")[Reinicio al enviar]],
  [#text(size: 7.5pt)[Campo en blanco o bloque electivo sin seleccionar.]],
  [#text(size: 7.5pt)[Completar todos los datos personales y marcar los 4 electivos antes de enviar.]],

  [#text(size: 7.5pt, weight: "bold")[Inscripción ya registrada]],
  [#text(size: 7.5pt)[El RUN ya completó el proceso este año.]],
  [#text(size: 7.5pt)[Revisa tu correo institucional para localizar el comprobante enviado.]],

  [#text(size: 7.5pt, weight: "bold")[No llegó el correo]],
  [#text(size: 7.5pt)[Filtro antispam o retraso de entrega.]],
  [#text(size: 7.5pt)[Revisar carpeta Spam. Si viste la confirmación verde, tus datos ya están guardados.]],

  [#text(size: 7.5pt, weight: "bold")[Error de conexión / base de datos]],
  [#text(size: 7.5pt)[Microcorte de red o sobrecarga temporal.]],
  [#text(size: 7.5pt)[Espera 10 segundos, recarga la página en el navegador y reintenta el envío.]]
)

#v(4pt)
= 8. Contacto y Soporte

Si presentas inconvenientes técnicos con la plataforma o requieres asistencia con tu cuenta institucional, puedes comunicarte con la *Unidad de Informática*:

#v(3pt)
#align(center)[
  #rect(
    width: 90%,
    fill: rgb("#f0fdf4"),
    stroke: 1pt + rgb("#86efac"),
    radius: 5pt,
    inset: 8pt,
    [
      #text(size: 10pt, weight: "bold", fill: rgb("#166534"))[Unidad de Informática — Colegio Talagante Garden School] \
      #v(2pt)
      #text(size: 8.5pt, fill: rgb("#1f2937"))[
        *Correos de contacto:* #link("mailto:admin@colegiotgs.cl")[admin\@colegiotgs.cl] | #link("mailto:ba.calderon@colegiotgs.cl")[ba.calderon\@colegiotgs.cl]
      ]
    ]
  )
]
