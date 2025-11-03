# from supabase import create_client, Client
from streamlit import secrets
from typing import List
from form_validate import get_supabase_client
import streamlit as st

@st.cache_data(ttl=3600)
def get_electives(level: str) -> List[List[str]]:
    """
    Fetches and categorizes electives from a Supabase table based on a given level.

    Args:
        level (str): The level to filter by, either "enabled_3medio" or "enabled_4medio".

    Returns:
        List[List[str]]: A list containing three lists, each corresponding to a group of electives.
                        For example, [[group1_electives], [group2_electives], [group3_electives]].
    """

    # 1. Determine the correct group column based on the 'level' parameter.
    #    This variable will be used dynamically later.
    groups = "group_3medio" if level == "enabled_3medio" else "group_4medio"

    # 2. Retrieve credentials from Streamlit's secrets.
    supabase: Client = get_supabase_client()

    # 3. Query the 'electives' table.
    #    Select 'id', 'name', 'area', and the dynamic 'groups' column.
    #    Filter rows where the 'level' column is True.
    response = (
        supabase.table("electives")
        .select("id", "name", "area", groups)
        .eq(level, True)
        .execute()
    )

    # 4. Use the dynamic 'groups' variable to filter the data.
    #    This ensures the code works for both 3rd and 4th-year levels.
    group_1 = [f'Área {row["area"]}: {row["name"]}' for row in response.data if row[groups] == 1]
    group_2 = [f'Área {row["area"]}: {row["name"]}' for row in response.data if row[groups] == 2]
    group_3 = [f'Área {row["area"]}: {row["name"]}' for row in response.data if row[groups] == 3]

    return [group_1, group_2, group_3]


