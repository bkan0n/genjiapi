from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import get

from utils.utilities import MAP_NAME_T  # noqa: TCH001

from ..root import BaseController
from .models import MapMasteryData

if TYPE_CHECKING:
    from asyncpg import Connection


class MasteryController(BaseController):
    path = "/mastery"
    tags = ["Mastery"]

    @get(path="/{user_id:int}")
    async def fetch_user_mastery(
        self,
        db_connection: Connection,
        user_id: int,
        map_name: MAP_NAME_T | None = None,
    ) -> list[MapMasteryData]:
        """Fetch Map Mastery for a particular user."""
        query = """
            WITH minimized_records AS (
                SELECT DISTINCT ON (r.map_code, m.map_name)
                    map_name
                FROM records r
                LEFT JOIN maps m ON r.map_code = m.map_code
                WHERE r.user_id = $1
            ),
            map_counts AS (
                SELECT map_name, count(map_name) AS amount
                FROM minimized_records
                GROUP BY map_name
            )
            SELECT
                amn.name as map_name,
                COALESCE(mc.amount, 0) AS amount
            FROM all_map_names amn
            LEFT JOIN map_counts mc ON mc.map_name = amn.name
            WHERE $2::text IS NULL OR amn.name = $2
            ORDER BY amn.name;
        """
        rows = await db_connection.fetch(query, user_id, map_name)
        return [MapMasteryData(**row) for row in rows]
