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
            WITH combined_names AS (
                SELECT
                    nickname AS name,
                    u.user_id
                FROM users u
                UNION DISTINCT
                SELECT global_name AS name,
                 user_id
                FROM user_global_names
            )
            SELECT name, user_id FROM combined_names ORDER BY similarity($1::text, name) DESC LIMIT $2::int
        """
        rows = await db_connection.fetch(query, value, page_size)
        return [CreatorAutocompleteResponse(**row) for row in rows]
