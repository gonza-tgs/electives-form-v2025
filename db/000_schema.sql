--
-- PostgreSQL database dump
--


-- Dumped from database version 17.11 (Debian 17.11-1.pgdg13+2)
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: validar_e_inscribir_electivos(text, text, text, text, text, text, text, integer, integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.validar_e_inscribir_electivos(p_run text, p_email text, p_curso_nombre text, p_electivo_1_full text, p_electivo_2_full text, p_electivo_3_full text, p_electivo_fg_nombre text, p_process_year integer, p_cupos_electivo integer, p_cupos_fg integer) RETURNS jsonb
    LANGUAGE plpgsql
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

    -- 2. Validar Usuario (CORREGIDO CON "RUN")
    SELECT * INTO v_student FROM public.students 
    WHERE "RUN" = v_run_limpio AND email = p_email AND class_id = v_curso_id;
    
    IF v_student IS NULL THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Datos de estudiante no coinciden. Verifica que tu RUN, email y curso (' || p_curso_nombre || ') sean correctos.');
    END IF;

    -- 3. Cargar datos de la clase (para inserts Y OBTENER NIVEL)
    SELECT * INTO v_class FROM public.class WHERE id = v_student.class_id;

    -- 4. Validar si ya está inscrito
    IF EXISTS (SELECT 1 FROM public.enrollments WHERE student_run = v_run_limpio AND process_year = p_process_year) THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Ya tienes una inscripción registrada para este año.');
    END IF;

    -- 5. Obtener IDs y Áreas de Electivos
    SELECT * INTO v_electivo_1 FROM public.electives WHERE name = SUBSTRING(p_electivo_1_full, 9);
    SELECT * INTO v_electivo_2 FROM public.electives WHERE name = SUBSTRING(p_electivo_2_full, 9);
    SELECT * INTO v_electivo_3 FROM public.electives WHERE name = SUBSTRING(p_electivo_3_full, 9);
    SELECT * INTO v_electivo_fg FROM public.general_edu WHERE name = p_electivo_fg_nombre;

    -- 6. Validar que los electivos existan
    IF v_electivo_1 IS NULL OR v_electivo_2 IS NULL OR v_electivo_3 IS NULL OR v_electivo_fg IS NULL THEN
         RETURN jsonb_build_object('valido', false, 'mensaje', 'Uno de los electivos seleccionados no se pudo encontrar en la base de datos.');
    END IF;

    -- 7. Validar que no sean de la misma área
    IF v_electivo_1.area = v_electivo_2.area AND v_electivo_2.area = v_electivo_3.area THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'No puedes inscribir 3 electivos de la misma área.');
    END IF;

    -- ==========================================================
    -- 8. Validar Cupos Electivo 1 (CORREGIDO CON NIVEL)
    -- ==========================================================
    SELECT COUNT(*) INTO v_cupos_actuales
    FROM public.enrollments e
    JOIN public.class c ON e.class_id = c.id
    WHERE e.elective_id = v_electivo_1.id
      AND e.process_year = p_process_year
      AND c.level = v_class.level; -- <-- SOLO CUENTA ALUMNOS DEL MISMO NIVEL

    IF v_cupos_actuales >= p_cupos_electivo THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo 1 sin cupos para tu nivel: ' || p_electivo_1_full);
    END IF;
    
    -- ==========================================================
    -- 9. Validar Cupos Electivo 2 (CORREGIDO CON NIVEL)
    -- ==========================================================
    SELECT COUNT(*) INTO v_cupos_actuales
    FROM public.enrollments e
    JOIN public.class c ON e.class_id = c.id
    WHERE e.elective_id = v_electivo_2.id
      AND e.process_year = p_process_year
      AND c.level = v_class.level; -- <-- SOLO CUENTA ALUMNOS DEL MISMO NIVEL

    IF v_cupos_actuales >= p_cupos_electivo THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo 2 sin cupos para tu nivel: ' || p_electivo_2_full);
    END IF;

    -- ==========================================================
    -- 10. Validar Cupos Electivo 3 (CORREGIDO CON NIVEL)
    -- ==========================================================
    SELECT COUNT(*) INTO v_cupos_actuales
    FROM public.enrollments e
    JOIN public.class c ON e.class_id = c.id
    WHERE e.elective_id = v_electivo_3.id
      AND e.process_year = p_process_year
      AND c.level = v_class.level; -- <-- SOLO CUENTA ALUMNOS DEL MISMO NIVEL

    IF v_cupos_actuales >= p_cupos_electivo THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo 3 sin cupos para tu nivel: ' || p_electivo_3_full);
    END IF;

    -- 11. Validar Cupos Electivo FG (Esta ya era correcta, filtraba por class_id)
    SELECT COUNT(*) INTO v_cupos_actuales FROM public.enrollments_ge 
    WHERE elective_id = v_electivo_fg.id AND class_id = v_class.id AND process_year = p_process_year;
     IF v_cupos_actuales >= p_cupos_fg THEN
        RETURN jsonb_build_object('valido', false, 'mensaje', 'Electivo de Formación General sin cupos para tu curso.');
    END IF;

    -- 12. Validar electivos previos
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

    -- 13. ¡Validación Exitosa! Insertar los datos.
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: class; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.class (
    id bigint NOT NULL,
    level bigint NOT NULL,
    name character varying,
    year bigint
);


--
-- Name: class_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.class ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.class_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: electives; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.electives (
    id bigint NOT NULL,
    name character varying NOT NULL,
    area character varying NOT NULL,
    group_3medio bigint NOT NULL,
    group_4medio bigint NOT NULL,
    enabled_3medio boolean NOT NULL,
    enabled_4medio boolean NOT NULL
);


--
-- Name: electives_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.electives ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.electives_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: enrollments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollments (
    id bigint NOT NULL,
    student_run text,
    elective_id bigint,
    process_year bigint,
    class_id bigint
);


--
-- Name: enrollments_ge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollments_ge (
    id bigint NOT NULL,
    elective_id bigint NOT NULL,
    process_year bigint NOT NULL,
    class_id bigint NOT NULL,
    student_run text
);


--
-- Name: enrollments_ge_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.enrollments_ge ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.enrollments_ge_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: enrollments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.enrollments ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.enrollments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: general_edu; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.general_edu (
    id bigint NOT NULL,
    name character varying NOT NULL,
    enabled_3medio bigint NOT NULL,
    enabled_4medio bigint NOT NULL
);


--
-- Name: general_edu_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.general_edu ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.general_edu_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: students; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.students (
    id bigint NOT NULL,
    "RUN" text NOT NULL,
    name text NOT NULL,
    lastname text NOT NULL,
    class_id bigint NOT NULL,
    email text NOT NULL
);


--
-- Name: students_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.students ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.students_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: class class_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class
    ADD CONSTRAINT class_pkey PRIMARY KEY (id);


--
-- Name: electives electives_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.electives
    ADD CONSTRAINT electives_id_key UNIQUE (id);


--
-- Name: electives electives_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.electives
    ADD CONSTRAINT electives_pkey PRIMARY KEY (id);


--
-- Name: enrollments enrollements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollements_pkey PRIMARY KEY (id);


--
-- Name: enrollments_ge enrollments_ge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments_ge
    ADD CONSTRAINT enrollments_ge_pkey PRIMARY KEY (id);


--
-- Name: enrollments enrollments_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_id_key UNIQUE (id);


--
-- Name: general_edu general_edu_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.general_edu
    ADD CONSTRAINT general_edu_id_key UNIQUE (id);


--
-- Name: general_edu general_edu_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.general_edu
    ADD CONSTRAINT general_edu_pkey PRIMARY KEY (id);


--
-- Name: students students_RUN_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT "students_RUN_key" UNIQUE ("RUN");


--
-- Name: students students_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (id);


--
-- Name: enrollments enrollements_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollements_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.class(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: enrollments enrollements_elective_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollements_elective_id_fkey FOREIGN KEY (elective_id) REFERENCES public.electives(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: enrollments enrollements_student_run_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollements_student_run_fkey FOREIGN KEY (student_run) REFERENCES public.students("RUN") ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: enrollments_ge enrollments_ge_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments_ge
    ADD CONSTRAINT enrollments_ge_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.class(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: enrollments_ge enrollments_ge_elective_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments_ge
    ADD CONSTRAINT enrollments_ge_elective_id_fkey FOREIGN KEY (elective_id) REFERENCES public.general_edu(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: enrollments_ge enrollments_ge_student_run_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments_ge
    ADD CONSTRAINT enrollments_ge_student_run_fkey FOREIGN KEY (student_run) REFERENCES public.students("RUN") ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: students students_class_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.class(id);


--
-- PostgreSQL database dump complete
--


