"""Genera el SQL que reemplaza la nómina (public.students) a partir de los Excel de Lirmi.

Entradas:
  - Uno o más Excel de Lirmi con una hoja por curso ("2º Medio A", "3º Medio B", ...).
    En cada hoja hay una fila de encabezado con RUN, NOMBRES y APELLIDOS (en cualquier orden).
  - La hoja "Correos" (exportada de Google Workspace), en cualquiera de esos Excel.

Fuentes de cada dato:
  - RUN, curso, nombres y apellidos: nómina de Lirmi.
  - Correo: hoja Correos. Si ahí falta el RUN, se busca por nombre completo exacto y único.

Cursos: 2° A -> 1, 2° B -> 2, 3° A -> 3, 3° B -> 4 (A = green, B = blue; ver CURSOS).

El SQL resultante contiene datos personales: escribirlo fuera del repositorio (por ejemplo,
en el scratchpad) y no subirlo a git.

Uso:
  uv run --no-project --with openpyxl python scripts/generar_nomina_sql.py \
      --anio 2026 --salida /ruta/fuera/del/repo/nomina.sql [--seco] archivo1.xlsx archivo2.xlsx
"""

import argparse
import re
import sys
import unicodedata

import openpyxl

# (nivel, sección en Lirmi) -> id en public.class. Debe coincidir con el CASE de validar_e_inscribir_electivos.
CURSOS = {(2, "A"): 1, (2, "B"): 2, (3, "A"): 3, (3, "B"): 4}


def norm_run(valor) -> str:
    return re.sub(r"[^0-9K]", "", str(valor).upper()) if valor is not None else ""


def dv_valido(run: str) -> bool:
    if len(run) < 2 or not run[:-1].isdigit():
        return False
    suma, factor = 0, 2
    for d in reversed(run[:-1]):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return run[-1] == {11: "0", 10: "K"}.get(resto, str(resto))


def norm_texto(valor) -> str:
    s = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def limpiar(valor) -> str:
    return " ".join(str(valor or "").split())


def sql_str(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def leer_correos(libros):
    hojas = [wb["Correos"] for wb in libros if "Correos" in wb.sheetnames]
    if len(hojas) != 1:
        sys.exit(f"Se esperaba exactamente una hoja 'Correos' entre los archivos; hay {len(hojas)}.")
    filas = list(hojas[0].iter_rows(values_only=True))
    enc = [norm_texto(c) for c in filas[0]]
    i_run = next(i for i, c in enumerate(enc) if c in ("rut", "run"))
    i_nom, i_ape = enc.index("nombres"), enc.index("apellidos")
    i_mail = next(i for i, c in enumerate(enc) if "correo" in c)
    por_run, sin_run, repetidos = {}, [], set()
    for f in filas[1:]:
        if not any(f):
            continue
        run = norm_run(f[i_run])
        mail = limpiar(f[i_mail]).lower()
        if not run:
            sin_run.append((norm_texto(f[i_nom]), norm_texto(f[i_ape]), mail))
        elif run in por_run and por_run[run] != mail:
            repetidos.add(run)
        else:
            por_run[run] = mail
    for run in repetidos:  # RUN con dos correos distintos: no se puede elegir.
        por_run.pop(run)
    return por_run, sin_run


def leer_nomina(libros):
    estudiantes = []
    for wb in libros:
        for ws in wb.worksheets:
            m = re.search(r"(\d)\D*medio\s*([A-Z])\s*$", ws.title, re.IGNORECASE)
            if ws.title == "Correos":
                continue
            if not m:
                sys.exit(f"No se reconoce el curso en la hoja '{ws.title}'.")
            curso = CURSOS.get((int(m.group(1)), m.group(2).upper()))
            if curso is None:
                sys.exit(f"La hoja '{ws.title}' no corresponde a un curso del proceso.")
            filas = list(ws.iter_rows(values_only=True))
            h = next(i for i, f in enumerate(filas) if any(norm_texto(c) == "run" for c in f))
            enc = [norm_texto(c) for c in filas[h]]
            i_run, i_nom, i_ape = enc.index("run"), enc.index("nombres"), enc.index("apellidos")
            for f in filas[h + 1:]:
                if f[i_run] is None:
                    if any(f):
                        sys.exit(f"Fila sin RUN con datos en la hoja '{ws.title}'.")
                    continue
                estudiantes.append(dict(
                    run=norm_run(f[i_run]), nombres=limpiar(f[i_nom]), apellidos=limpiar(f[i_ape]),
                    curso=curso, hoja=ws.title,
                ))
    return estudiantes


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archivos", nargs="+")
    p.add_argument("--anio", type=int, required=True, help="Año de la nómina (año escolar en curso).")
    p.add_argument("--salida", required=True)
    p.add_argument("--seco", action="store_true", help="Terminar con ROLLBACK en vez de COMMIT.")
    a = p.parse_args()

    libros = [openpyxl.load_workbook(f, data_only=True) for f in a.archivos]
    por_run, sin_run = leer_correos(libros)
    estudiantes = leer_nomina(libros)

    errores = []
    for e in estudiantes:
        if not dv_valido(e["run"]):
            errores.append(f"{e['hoja']}: RUN con dígito verificador inválido")
        if not e["nombres"] or not e["apellidos"]:
            errores.append(f"{e['hoja']}: estudiante sin nombres o apellidos")
        mail = por_run.get(e["run"])
        if not mail:
            hits = [m for n, ap, m in sin_run
                    if n == norm_texto(e["nombres"]) and ap == norm_texto(e["apellidos"])]
            mail = hits[0] if len(hits) == 1 else None
        if not mail:
            errores.append(f"{e['hoja']}: estudiante sin correo en la hoja Correos")
        e["email"] = mail
    runs = [e["run"] for e in estudiantes]
    mails = [e["email"] for e in estudiantes if e["email"]]
    if len(set(runs)) != len(runs):
        errores.append("Hay RUN repetidos en la nómina")
    if len(set(mails)) != len(mails):
        errores.append("Hay correos repetidos en la nómina")
    if errores:
        sys.exit("No se generó el SQL:\n  " + "\n  ".join(errores))

    valores = ",\n".join(
        f"    ({sql_str(e['run'])}, {sql_str(e['nombres'])}, {sql_str(e['apellidos'])}, {e['curso']}, {sql_str(e['email'])})"
        for e in estudiantes
    )
    por_curso = {c: sum(e["curso"] == c for e in estudiantes) for c in sorted(set(CURSOS.values()))}
    chequeo = " AND ".join(
        f"(SELECT count(*) FROM public.students WHERE class_id = {c}) = {n}" for c, n in por_curso.items()
    )
    sql = f"""-- Nómina {a.anio} generada por scripts/generar_nomina_sql.py. CONTIENE DATOS PERSONALES: no versionar.
BEGIN;

-- Sin estas FK con cascada, vaciar students no toca el historial (migración 002).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE confrelid = 'public.students'::regclass AND contype = 'f') THEN
        RAISE EXCEPTION 'Hay FK hacia students: aplicar db/002_cursados_y_historial.sql antes de cargar la nómina.';
    END IF;
END $$;

DELETE FROM public.students;

INSERT INTO public.students ("RUN", name, lastname, class_id, email) VALUES
{valores};

UPDATE public.class SET year = {a.anio};

DO $$
BEGIN
    IF NOT ({chequeo}) OR (SELECT count(*) FROM public.students) <> {len(estudiantes)} THEN
        RAISE EXCEPTION 'La cantidad de estudiantes por curso no coincide con la nómina.';
    END IF;
END $$;

SELECT c.id, c.level, c.name, c.year, count(s.id) AS estudiantes
FROM public.class c LEFT JOIN public.students s ON s.class_id = c.id
GROUP BY c.id ORDER BY c.id;

{'ROLLBACK' if a.seco else 'COMMIT'};
"""
    with open(a.salida, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"SQL escrito en {a.salida} ({'seco' if a.seco else 'COMMIT'}): {len(estudiantes)} estudiantes, por curso {por_curso}")


if __name__ == "__main__":
    main()
