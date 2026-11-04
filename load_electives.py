from typing import List

import streamlit as st

from form_validate import get_pool

# Las columnas no pueden pasarse como parámetros SQL, por eso cada nivel tiene su consulta fija.
ELECTIVES_SQL = {
    "enabled_3medio": "SELECT name, area, group_3medio FROM public.electives WHERE enabled_3medio ORDER BY id",
    "enabled_4medio": "SELECT name, area, group_4medio FROM public.electives WHERE enabled_4medio ORDER BY id",
}

@st.cache_data(ttl=3600)
def get_electives(level: str) -> List[List[str]]:
    """
    Fetches and categorizes electives from the database based on a given level.

    Args:
        level (str): The level to filter by, either "enabled_3medio" or "enabled_4medio".

    Returns:
        List[List[str]]: A list containing three lists, each corresponding to a group of electives.
                        For example, [[group1_electives], [group2_electives], [group3_electives]].
    """
    with get_pool().connection() as conn:
        rows = conn.execute(ELECTIVES_SQL[level]).fetchall()

    groups = [[], [], []]
    for name, area, group in rows:
        if group in (1, 2, 3):
            groups[group - 1].append(f"Área {area}: {name}")

    return groups
