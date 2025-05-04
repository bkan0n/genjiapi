from textwrap import dedent

CTE_FILTER_TEMPLATES = {
    "mechanic": dedent("""
        SELECT map_id
        FROM maps.mechanic_links m1
        JOIN maps.mechanics m2 ON m1.mechanic_id = m2.id
        WHERE m2.name = ${}
    """),
    "restriction": dedent("""
        SELECT map_id
        FROM maps.restriction_links r1
        JOIN maps.restrictions r2 ON r1.restriction_id = r2.id
        WHERE r2.name = ${}
    """),
    "creator": dedent("""
        SELECT map_id
        FROM maps.creators c
        WHERE c.user_id = ${}
    """),
    "rating": dedent("""
        SELECT map_id
        FROM maps.ratings
        GROUP BY map_id
        HAVING avg(quality) >= ${}
    """)
    # add more templates as needed
}

WHERE_TEMPLATES = {
    "name": "m.name=${}",
    "map_type": "${}=ANY(m.map_type)",
    "official": "m.status='official'",
    "playtest": "m.status='playtest'",
    "archived": "m.archived=${}",
}

WHERE_DIFFICULTY_TEMPLATES = {
    "Easy": "m.difficulty >= 0 AND m.difficulty < 2.35",
    "Medium": "m.difficulty >= 2.35 AND m.difficulty < 4.12",
    "Hard": "m.difficulty >= 4.12 AND m.difficulty < 5.88",
    "Very Hard": "m.difficulty >= 5.88 AND m.difficulty < 7.65",
    "Extreme": "m.difficulty >= 7.65 AND m.difficulty < 9.41",
    "Hell": "m.difficulty >= 9.41 AND m.difficulty <= 10.0",
}



def build_sql(
    *,
    templates: dict[str, str],
    selections: list[str],
    start_index: int = 1,
    pre: str = "",
    post: str = "",
    split: str = "\n",
) -> tuple[str, int]:
    _selections = []
    current_index = start_index
    for key in selections:
        template = templates[key]
        filled = template.format(current_index)
        _selections.append(filled.strip())
        current_index += 1
    if not _selections:
        return "", start_index
    return pre + (f"{split}".join(_selections)) + post, current_index

def build_map_search_sql(
    *,
    pre_filters: list[str],
    where_filters: list[str],
    where_difficulty: str
) -> str:
    pre_select_sql, next_index = build_sql(
        templates=CTE_FILTER_TEMPLATES,
        selections=pre_filters,
        start_index=1,
        pre="WITH intersection_map_ids AS (\n",
        post="\n)\n",
        split="\nINTERSECT\n"
    )

    where_sql, final_index = build_sql(
        templates=WHERE_TEMPLATES,
        selections=where_filters,
        start_index=next_index,
        pre="WHERE\n",
        split=" AND\n"
    )

    if where_difficulty:
        difficulty_clause = WHERE_DIFFICULTY_TEMPLATES[where_difficulty]
        if where_sql:
            where_sql += f"\nAND {difficulty_clause}"
        else:
            where_sql = f"WHERE\n{difficulty_clause}"

    return f"""
    {pre_select_sql}
    SELECT
        imi.map_id,
        map_type,
        m.map_code,
        m.description,
        m.status,
        m.archived,
        m.name,
        array_agg(DISTINCT m2.name) AS mechanics,
        array_agg(DISTINCT r2.name) AS restrictions,
        array_agg(DISTINCT c.user_id) AS creator_ids,
        array_agg(DISTINCT u.nickname) AS creator_names,
        m.checkpoints
    FROM intersection_map_ids imi
    LEFT JOIN core.maps m ON imi.map_id = m.id
    LEFT JOIN maps.mechanic_links m1 ON m1.map_id = m.id
    LEFT JOIN maps.mechanics m2 ON m1.mechanic_id = m2.id
    LEFT JOIN maps.restriction_links r1 ON r1.map_id = m.id
    LEFT JOIN maps.restrictions r2 ON r1.restriction_id = r2.id
    LEFT JOIN maps.creators c ON m.id = c.map_id
    LEFT JOIN core.users u ON c.user_id = u.id
    {where_sql}
    GROUP BY m.checkpoints,
        imi.map_id,
        m.name,
        m.map_code,
        m.description,
        m.map_type,
        m.archived,
        m.status;
    """


selected_pre_filters = ["restriction", "mechanic", "rating", "creator"]
selected_pre_filters_value = ["Dash Start", "Bhop", 1, 463743342937636874]
selected_where_filters = ["name", "archived", "map_type"]
selected_where_filters_value = ["Blizzard World", False, "Classic"]
selected_where_difficulty = "Hard"

main_sql = build_map_search_sql(pre_filters=selected_pre_filters, where_filters=selected_where_filters, where_difficulty=selected_where_difficulty)

print(main_sql)

print(selected_pre_filters_value + selected_where_filters_value)



