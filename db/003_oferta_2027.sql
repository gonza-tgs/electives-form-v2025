-- Oferta de electivos 2027 (Plan de Formación Diferenciada, Forma N° 01/26).
--
-- Se trabaja por id: los nombres oficiales son los que ya están en public.electives y
-- public.general_edu, y cada electivo es una sola fila para ambos niveles (así se conserva
-- el historial para la regla "ya lo cursaste el año pasado").
-- Grupo 0 = no se dicta en ese nivel (load_electives.py solo usa 1, 2 y 3).
--
-- Antes de aplicar: backup (scripts/descargar_backup.sh).

BEGIN;

CREATE TEMP TABLE oferta (
    id bigint PRIMARY KEY,
    name text NOT NULL,          -- solo para verificar que el id es el esperado
    group_3medio bigint NOT NULL,
    group_4medio bigint NOT NULL
) ON COMMIT DROP;

INSERT INTO oferta (id, name, group_3medio, group_4medio) VALUES
    ( 1, 'Biología celular y molecular',                           2, 0),
    ( 2, 'Ciencias del ejercicio físico y deportivo',              3, 1),
    ( 3, 'Ciencias de la Salud',                                   3, 0),
    ( 4, 'Comprensión histórica del presente',                     3, 3),
    ( 5, 'Diseño y arquitectura',                                  1, 0),
    ( 6, 'Economía y sociedad',                                    1, 0),
    ( 7, 'Participación y argumentación en democracia',            2, 0),
    ( 9, 'Probabilidades y estadística descriptiva e inferencial', 1, 0),
    (10, 'Artes visuales, audiovisuales y multimediales',          0, 2),
    (11, 'Interpretación Musical',                                 2, 3),
    (12, 'Física',                                                 0, 3),
    (13, 'Taller de Literatura',                                   0, 2),
    (14, 'Límites, derivadas e integrales',                        0, 1),
    (16, 'Seminario de Filosofía',                                 0, 1),
    (18, 'Biología de los ecosistemas',                            0, 2);

-- Si algún id no corresponde al nombre esperado, la base no es la que se revisó: abortar.
DO $$
DECLARE v_bad text;
BEGIN
    SELECT string_agg(format('id %s: esperado "%s", hay "%s"', o.id, o.name, coalesce(e.name, '(no existe)')), '; ')
    INTO v_bad
    FROM oferta o LEFT JOIN public.electives e ON e.id = o.id
    WHERE e.name IS DISTINCT FROM o.name;
    IF v_bad IS NOT NULL THEN
        RAISE EXCEPTION 'Ids no coinciden: %', v_bad;
    END IF;
END $$;

-- Lo que no está en la oferta queda deshabilitado (no se borra: lo usa el historial).
UPDATE public.electives e
SET group_3medio = coalesce((SELECT o.group_3medio FROM oferta o WHERE o.id = e.id), 0),
    group_4medio = coalesce((SELECT o.group_4medio FROM oferta o WHERE o.id = e.id), 0);

UPDATE public.electives
SET enabled_3medio = group_3medio > 0,
    enabled_4medio = group_4medio > 0;

-- Formación general (plan común electivo): ambos niveles eligen entre estas dos.
-- Ojo: el formulario toma la lista de ELECTIVOS_FG en los secrets, no de estas columnas.
UPDATE public.general_edu
SET enabled_3medio = CASE WHEN id IN (1, 3) THEN 1 ELSE 0 END,
    enabled_4medio = CASE WHEN id IN (1, 3) THEN 1 ELSE 0 END;

-- Cada nivel debe quedar con 3 grupos (1, 2, 3) de 3 electivos, uno por área.
DO $$
DECLARE v_bad text; v_grupos int;
BEGIN
    SELECT string_agg(format('%s grupo %s: %s electivos, %s áreas', nivel, grupo, n, areas), '; ') INTO v_bad
    FROM (
        SELECT 'III°' AS nivel, group_3medio AS grupo, count(*) AS n, count(DISTINCT area) AS areas
        FROM public.electives WHERE enabled_3medio GROUP BY group_3medio
        UNION ALL
        SELECT 'IV°', group_4medio, count(*), count(DISTINCT area)
        FROM public.electives WHERE enabled_4medio GROUP BY group_4medio
    ) t
    WHERE n <> 3 OR areas <> 3 OR grupo NOT IN (1, 2, 3);

    SELECT count(DISTINCT group_3medio) + (SELECT count(DISTINCT group_4medio) FROM public.electives WHERE enabled_4medio)
    INTO v_grupos FROM public.electives WHERE enabled_3medio;

    IF v_bad IS NOT NULL OR v_grupos <> 6 THEN
        RAISE EXCEPTION 'Oferta inconsistente: % (grupos: %)', coalesce(v_bad, '-'), v_grupos;
    END IF;
END $$;

COMMIT;
