from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import get

from ..root import BaseController
from .models import (
    CreatorAutocompleteResponse,
    MapBaseAutocompleteResponse,
    MapCodeAutocompleteResponse,
    MapNameAutocompleteResponse,
)

if TYPE_CHECKING:
    from asyncpg import Connection


class AutocompleteController(BaseController):
    path = "/autocomplete"
    tags = ["Autocomplete"]

    @get(path="/map-names/{locale:str}")
    async def get_map_names_autocomplete(
        self,
        db_connection: Connection,
        value: str,
        page_size: int = 10,
        locale: str = "en",
    ) -> list[MapNameAutocompleteResponse]:
        """Get autocomplete map names."""
        query = """
            SELECT
                name as map_name,
                CASE
                    WHEN $3::text = 'cn' THEN cn
                    WHEN $3::text = 'jp' THEN jp
                    ELSE name
                END AS translated_map_name
            FROM all_map_names
            ORDER BY CASE
                WHEN $3::text = 'cn' THEN similarity($1::text, cn)
                WHEN $3::text = 'jp' THEN similarity($1::text, jp)
                ELSE similarity($1::text, name)
            END DESC
            LIMIT $2::int
         """
        rows = await db_connection.fetch(query, value, page_size, locale)
        return [MapNameAutocompleteResponse(**row) for row in rows]

    @get(path="/map-types")
    async def get_map_types_autocomplete(
        self,
        db_connection: Connection,
        value: str,
        page_size: int = 10,
    ) -> list[MapBaseAutocompleteResponse]:
        """Get autocomplete map types."""
        query = "SELECT name FROM all_map_types ORDER BY similarity($1::text, name) DESC LIMIT $2::int"
        rows = await db_connection.fetch(query, value, page_size)
        return [MapBaseAutocompleteResponse(**row) for row in rows]

    @get(path="/map-restrictions")
    async def get_map_restrictions_autocomplete(
        self,
        db_connection: Connection,
    ) -> list[MapBaseAutocompleteResponse]:
        """Get autocomplete for map restrictions."""
        query = "SELECT name FROM all_map_restrictions ORDER BY order_num"
        rows = await db_connection.fetch(query)
        return [MapBaseAutocompleteResponse(**row) for row in rows]

    @get(path="/map-mechanics")
    async def get_map_mechanics_autocomplete(
        self,
        db_connection: Connection,
    ) -> list[MapBaseAutocompleteResponse]:
        """Get autocomplete for map mechanics."""
        query = "SELECT name FROM all_map_mechanics ORDER BY order_num"
        rows = await db_connection.fetch(query)
        return [MapBaseAutocompleteResponse(**row) for row in rows]

    @get(path="/map-codes")
    async def get_map_codes_autocomplete(
        self,
        db_connection: Connection,
        value: str,
        page_size: int = 10,
    ) -> list[MapCodeAutocompleteResponse]:
        """Get autocomplete for map codes."""
        query = "SELECT map_code FROM maps ORDER BY similarity($1::text, map_code) DESC LIMIT $2::int"
        rows = await db_connection.fetch(query, value, page_size)
        return [MapCodeAutocompleteResponse(**row) for row in rows]

    @get(path="/creators")
    async def get_creators_autocomplete(
        self,
        db_connection: Connection,
        value: str,
        page_size: int = 10,
    ) -> list[CreatorAutocompleteResponse]:
        """Get autocomplete for creators."""
        query = """
            WITH matches AS (
                SELECT u.user_id, name
                FROM users u
                CROSS JOIN LATERAL (
                    VALUES (u.nickname), (u.global_name)
                ) AS name_list(name)
                WHERE name % $1
            
                UNION
            
                SELECT o.user_id, o.username AS name
                FROM user_overwatch_usernames o
                WHERE o.username % $1
            ),
            ranked_users AS (
                SELECT user_id, MAX(similarity(name, $1)) AS sim
                FROM matches
                GROUP BY user_id
                ORDER BY sim DESC
                LIMIT 10
            ),
            user_names AS (
                SELECT
                    u.user_id,
                    ARRAY_REMOVE(
                        ARRAY[u.nickname, u.global_name ] || ARRAY_AGG(own_all.username),
                        NULL
                    ) AS all_usernames
                FROM ranked_users ru
                JOIN users u ON u.user_id = ru.user_id
                LEFT JOIN user_overwatch_usernames own_all ON u.user_id = own_all.user_id
                GROUP BY u.user_id, u.nickname, u.global_name, sim
                ORDER BY sim DESC
            )
            SELECT user_id, ARRAY_TO_STRING(ARRAY(SELECT DISTINCT * FROM unnest(all_usernames)), ', ') AS name
            FROM user_names LIMIT $2::int;
        """

        rows = await db_connection.fetch(query, value, page_size)
        return [CreatorAutocompleteResponse(**row) for row in rows]
