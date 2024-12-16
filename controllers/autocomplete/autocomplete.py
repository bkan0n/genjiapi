from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import get

from ..root import BaseController
from .models import (
    CreatorAutocompleteResponse,
    MapCodeAutocompleteResponse,
    MapNameAutocompleteResponse,
)

if TYPE_CHECKING:
    from asyncpg import Connection


class AutocompleteController(BaseController):
    path = "/autocomplete"
    tags = ["Autocomplete"]

    @get(path="/map-names")
    async def get_map_names_autocomplete(
        self,
        db_connection: Connection,
        value: str,
        page_size: int = 10,
    ) -> list[MapNameAutocompleteResponse]:
        """Get autocomplete map names."""
        query = "SELECT name FROM all_map_names ORDER BY similarity($1::text, name) DESC LIMIT $2::int"
        rows = await db_connection.fetch(query, value, page_size)
        return [MapNameAutocompleteResponse(**row) for row in rows]

    @get(path="/map-types")
    async def get_map_types_autocomplete(
        self,
        db_connection: Connection,
        value: str,
        page_size: int = 10,
    ) -> list[MapNameAutocompleteResponse]:
        """Get autocomplete map types."""
        query = "SELECT name FROM all_map_types ORDER BY similarity($1::text, name) DESC LIMIT $2::int"
        rows = await db_connection.fetch(query, value, page_size)
        return [MapNameAutocompleteResponse(**row) for row in rows]

    @get(path="/map-restrictions")
    async def get_map_restrictions_autocomplete(
        self,
        db_connection: Connection,
    ) -> list[MapNameAutocompleteResponse]:
        """Get autocomplete for map restrictions."""
        query = "SELECT name FROM all_map_restrictions ORDER BY order_num"
        rows = await db_connection.fetch(query)
        return [MapNameAutocompleteResponse(**row) for row in rows]

    @get(path="/map-mechanics")
    async def get_map_mechanics_autocomplete(
        self,
        db_connection: Connection,
    ) -> list[MapNameAutocompleteResponse]:
        """Get autocomplete for map mechanics."""
        query = "SELECT name FROM all_map_mechanics ORDER BY order_num"
        rows = await db_connection.fetch(query)
        return [MapNameAutocompleteResponse(**row) for row in rows]

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
                SELECT nickname AS name
                FROM users u
                UNION DISTINCT
                SELECT global_name AS name
                FROM user_global_names
            )
            SELECT name FROM combined_names ORDER BY similarity($1::text, name) DESC LIMIT $2::int
        """
        rows = await db_connection.fetch(query, value, page_size)
        return [CreatorAutocompleteResponse(**row) for row in rows]
