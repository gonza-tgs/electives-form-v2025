-- Cambio en la oferta 2027 de IV° medio (pedido de coordinación, 17-11-2026):
-- sale Interpretación Musical y entra Creación y composición musical, en el mismo grupo 3 y área C.
-- En III° medio Interpretación Musical sigue igual (grupo 2).
--
-- Antes de aplicar: backup (scripts/descargar_backup.sh).
-- Después de aplicar: redesplegar electivos4 (la lista de electivos queda en caché 1 hora).

BEGIN;

-- Si la base no está como la dejó 003, abortar.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.electives
                   WHERE id = 11 AND name = 'Interpretación Musical' AND area = 'C'
                     AND group_4medio = 3 AND enabled_4medio) THEN
        RAISE EXCEPTION 'Interpretación Musical (id 11) no está en IV° grupo 3: la base no es la esperada';
    END IF;
    IF EXISTS (SELECT 1 FROM public.electives WHERE id = 19 OR name ILIKE 'Creación y composición musical') THEN
        RAISE EXCEPTION 'Ya existe el id 19 o Creación y composición musical';
    END IF;
END $$;

UPDATE public.electives
SET group_4medio = 0, enabled_4medio = false
WHERE id = 11;

INSERT INTO public.electives (id, name, area, group_3medio, group_4medio, enabled_3medio, enabled_4medio)
VALUES (19, 'Creación y composición musical', 'C', 0, 3, false, true);

-- La identidad no debe volver a entregar un id ya usado.
SELECT setval(pg_get_serial_sequence('public.electives', 'id'), (SELECT max(id) FROM public.electives));

-- Cada nivel debe quedar con 3 grupos (1, 2, 3) de 3 electivos, uno por área (mismo chequeo que 003).
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
