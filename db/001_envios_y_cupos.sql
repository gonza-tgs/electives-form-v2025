-- Evita envíos múltiples y sobrecupo en inscripciones simultáneas.
-- Deja a la app con permisos mínimos: leer el catálogo y ejecutar la función.
-- El rol electivos_app se crea sin login; su contraseña se define fuera del repo.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'electivos_owner') THEN
        CREATE ROLE electivos_owner NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'electivos_app') THEN
        CREATE ROLE electivos_app NOLOGIN;
    END IF;
END
$$;

-- Última barrera contra duplicados, además del bloqueo de la función.
CREATE UNIQUE INDEX enrollments_student_elective_year_key
    ON public.enrollments (student_run, elective_id, process_year);
CREATE UNIQUE INDEX enrollments_ge_student_year_key
    ON public.enrollments_ge (student_run, process_year);

CREATE OR REPLACE FUNCTION public.validar_e_inscribir_electivos(
    p_run text,
    p_email text,
    p_curso_nombre text,
    p_electivo_1_full text,
    p_electivo_2_full text,
    p_electivo_3_full text,
    p_electivo_fg_nombre text,
    p_process_year integer,
    p_cupos_electivo integer,
    p_cupos_fg integer
) RETURNS jsonb
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = pg_catalog, public, pg_temp
    AS $$
DECLARE
    v_student record;
    v_class record;
    v_electivo_1 record;
    v_electivo_2 record;
    v_electivo_3 record;
    v_electivo_fg record;
    v_run_limpio TEXT;
    v_curso_id INT;
    v_cupos_actuales INT;
    v_previous_process_year INT;
    v_electivos_previos BIGINT[];
    v_electivos_nuevos BIGINT[];
    v_fg_previo BIGINT;
BEGIN
    -- 0. Limpiar y estandarizar entradas
    v_run_limpio := UPPER(REPLACE(p_run, '-', ''));
    p_email := lower(trim(p_email));

    -- 1. Validar Curso (Lógica del CURSOS_MAP)
    v_curso_id := CASE p_curso_nombre
        WHEN '2 medio G' THEN 1
        WHEN '2 medio B' THEN 2
        WHEN '3 medio G' THEN 3
        WHEN '3 medio B' THEN 4
        ELSE NULL
    END;

    IF v_curso_id IS NULL THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'El curso seleccionado (' || p_curso_nombre || ') no es válido.');
    END IF;

    -- 2. Validar Usuario
    SELECT * INTO v_student FROM public.students
    WHERE "RUN" = v_run_limpio AND email = p_email AND class_id = v_curso_id;

    IF v_student IS NULL THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Datos de estudiante no coinciden. Verifica que tu RUN, email y curso (' || p_curso_nombre || ') sean correctos.');
    END IF;

    -- 3. Un solo envío a la vez por estudiante y año. Se libera al terminar la transacción.
    PERFORM pg_advisory_xact_lock(hashtextextended(v_run_limpio || ':' || p_process_year, 0));

    -- 4. Cargar datos de la clase (para inserts y para obtener el nivel)
    SELECT * INTO v_class FROM public.class WHERE id = v_student.class_id;

    -- 5. Obtener IDs y Áreas de Electivos
    SELECT * INTO v_electivo_1 FROM public.electives WHERE name = SUBSTRING(p_electivo_1_full, 9);
    SELECT * INTO v_electivo_2 FROM public.electives WHERE name = SUBSTRING(p_electivo_2_full, 9);
    SELECT * INTO v_electivo_3 FROM public.electives WHERE name = SUBSTRING(p_electivo_3_full, 9);
    SELECT * INTO v_electivo_fg FROM public.general_edu WHERE name = p_electivo_fg_nombre;

    -- 6. Validar que los electivos existan
    IF v_electivo_1 IS NULL OR v_electivo_2 IS NULL OR v_electivo_3 IS NULL OR v_electivo_fg IS NULL THEN
         RETURN jsonb_build_object('valido', false, 'mensaje', 'Uno de los electivos seleccionados no se pudo encontrar en la base de datos.');
    END IF;

    -- 7. Si ya está inscrito: repetir lo mismo es éxito sin cambios; otra selección se rechaza.
    SELECT array_agg(elective_id ORDER BY elective_id) INTO v_electivos_previos
    FROM public.enrollments WHERE student_run = v_run_limpio AND process_year = p_process_year;

    SELECT elective_id INTO v_fg_previo
    FROM public.enrollments_ge WHERE student_run = v_run_limpio AND process_year = p_process_year;

    IF v_electivos_previos IS NOT NULL OR v_fg_previo IS NOT NULL THEN
        SELECT array_agg(x ORDER BY x) INTO v_electivos_nuevos
        FROM unnest(ARRAY[v_electivo_1.id, v_electivo_2.id, v_electivo_3.id]) AS x;

        IF v_electivos_previos = v_electivos_nuevos AND v_fg_previo = v_electivo_fg.id THEN
            RETURN jsonb_build_object('valido', true, 'mensaje', 'Tu inscripción ya estaba registrada.');
        END IF;

        RETURN jsonb_build_object('valido', false, 'mensaje', 'Ya tienes una inscripción registrada para este año.');
    END IF;

    -- 8. Validar que no sean de la misma área
    IF v_electivo_1.area = v_electivo_2.area AND v_electivo_2.area = v_electivo_3.area THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'No puedes inscribir 3 electivos de la misma área.');
    END IF;

    -- 9. Bloquear los cupos elegidos antes de contar, siempre en el mismo orden para evitar deadlocks.
    PERFORM 1 FROM public.electives
    WHERE id IN (v_electivo_1.id, v_electivo_2.id, v_electivo_3.id)
    ORDER BY id
    FOR NO KEY UPDATE;

    PERFORM 1 FROM public.general_edu WHERE id = v_electivo_fg.id FOR NO KEY UPDATE;

    -- 10. Validar Cupos Electivo 1 (solo cuenta alumnos del mismo nivel)
    SELECT COUNT(*) INTO v_cupos_actuales
    FROM public.enrollments e
    JOIN public.class c ON e.class_id = c.id
    WHERE e.elective_id = v_electivo_1.id
      AND e.process_year = p_process_year
      AND c.level = v_class.level;

    IF v_cupos_actuales >= p_cupos_electivo THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo 1 sin cupos para tu nivel: ' || p_electivo_1_full);
    END IF;

    -- 11. Validar Cupos Electivo 2 (solo cuenta alumnos del mismo nivel)
    SELECT COUNT(*) INTO v_cupos_actuales
    FROM public.enrollments e
    JOIN public.class c ON e.class_id = c.id
    WHERE e.elective_id = v_electivo_2.id
      AND e.process_year = p_process_year
      AND c.level = v_class.level;

    IF v_cupos_actuales >= p_cupos_electivo THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo 2 sin cupos para tu nivel: ' || p_electivo_2_full);
    END IF;

    -- 12. Validar Cupos Electivo 3 (solo cuenta alumnos del mismo nivel)
    SELECT COUNT(*) INTO v_cupos_actuales
    FROM public.enrollments e
    JOIN public.class c ON e.class_id = c.id
    WHERE e.elective_id = v_electivo_3.id
      AND e.process_year = p_process_year
      AND c.level = v_class.level;

    IF v_cupos_actuales >= p_cupos_electivo THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo 3 sin cupos para tu nivel: ' || p_electivo_3_full);
    END IF;

    -- 13. Validar Cupos Electivo FG (por curso)
    SELECT COUNT(*) INTO v_cupos_actuales FROM public.enrollments_ge
    WHERE elective_id = v_electivo_fg.id AND class_id = v_class.id AND process_year = p_process_year;
    IF v_cupos_actuales >= p_cupos_fg THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo de Formación General sin cupos para tu curso.');
    END IF;

    -- 14. Validar electivos previos
    v_previous_process_year := p_process_year - 1;
    IF EXISTS (SELECT 1 FROM public.enrollments WHERE student_run = v_run_limpio AND elective_id = v_electivo_1.id AND process_year = v_previous_process_year) THEN
         RETURN jsonb_build_object('valido', false, 'mensaje', 'Ya cursaste el electivo ' || p_electivo_1_full || ' el año pasado.');
    END IF;
    IF EXISTS (SELECT 1 FROM public.enrollments WHERE student_run = v_run_limpio AND elective_id = v_electivo_2.id AND process_year = v_previous_process_year) THEN
         RETURN jsonb_build_object('valido', false, 'mensaje', 'Ya cursaste el electivo ' || p_electivo_2_full || ' el año pasado.');
    END IF;
    IF EXISTS (SELECT 1 FROM public.enrollments WHERE student_run = v_run_limpio AND elective_id = v_electivo_3.id AND process_year = v_previous_process_year) THEN
         RETURN jsonb_build_object('valido', false, 'mensaje', 'Ya cursaste el electivo ' || p_electivo_3_full || ' el año pasado.');
    END IF;

    -- 15. Validación exitosa: insertar los datos.
    INSERT INTO public.enrollments (student_run, elective_id, process_year, class_id)
    VALUES (v_run_limpio, v_electivo_1.id, p_process_year, v_class.id),
           (v_run_limpio, v_electivo_2.id, p_process_year, v_class.id),
           (v_run_limpio, v_electivo_3.id, p_process_year, v_class.id);

    INSERT INTO public.enrollments_ge (student_run, elective_id, process_year, class_id)
    VALUES (v_run_limpio, v_electivo_fg.id, p_process_year, v_class.id);

    RETURN jsonb_build_object('valido', true, 'mensaje', 'Inscripción exitosa.');

EXCEPTION
    -- Capturar cualquier error inesperado
    WHEN others THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Error interno del servidor: ' || SQLERRM);
END;
$$;

-- La función corre como electivos_owner, sin privilegios de superusuario.
ALTER TABLE public.class OWNER TO electivos_owner;
ALTER TABLE public.electives OWNER TO electivos_owner;
ALTER TABLE public.enrollments OWNER TO electivos_owner;
ALTER TABLE public.enrollments_ge OWNER TO electivos_owner;
ALTER TABLE public.general_edu OWNER TO electivos_owner;
ALTER TABLE public.students OWNER TO electivos_owner;
ALTER FUNCTION public.validar_e_inscribir_electivos(text, text, text, text, text, text, text, integer, integer, integer) OWNER TO electivos_owner;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON FUNCTION public.validar_e_inscribir_electivos(text, text, text, text, text, text, text, integer, integer, integer) FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO electivos_app;
GRANT SELECT ON public.electives TO electivos_app;
GRANT EXECUTE ON FUNCTION public.validar_e_inscribir_electivos(text, text, text, text, text, text, text, integer, integer, integer) TO electivos_app;

COMMIT;
