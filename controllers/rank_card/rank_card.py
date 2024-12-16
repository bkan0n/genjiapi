from __future__ import annotations

import asyncio
import io

import asyncpg  # noqa: TCH002
from litestar import get
from litestar.response import Stream

from ..root import BaseController
from .utils import RankCardBuilder, fetch_user_rank_data, find_highest_rank


class RankCardController(BaseController):
    path = "/rank_card"
    tags = ["Rank Card"]

    @get(path="/{user_id:int}")
    async def fetch_rank_card(
        self,
        db_connection: asyncpg.Connection,
        user_id: int,
    ) -> Stream:
        """Fetch rank card."""
        totals = await self._get_map_totals(db_connection)
        rank_data = await fetch_user_rank_data(db_connection, user_id, True, True)

        world_records = await self._get_world_record_count(db_connection, user_id)
        maps = await self._get_maps_count(db_connection, user_id)
        playtests = await self._get_playtests_count(db_connection, user_id)

        rank = find_highest_rank(rank_data)

        background = await self._get_background_choice(db_connection, user_id)

        nickname = await db_connection.fetchval("SELECT nickname FROM users WHERE user_id = $1;", user_id)

        data = {
            "rank": rank,
            "name": nickname,
            "bg": background,
            "maps": maps,
            "playtests": playtests,
            "world_records": world_records,
        }

        for row in rank_data:
            data[row.difficulty] = {
                "completed": row.completions,
                "gold": row.gold,
                "silver": row.silver,
                "bronze": row.bronze,
            }

        data["Beginner"] = {
            "completed": 0,
            "gold": 0,
            "silver": 0,
            "bronze": 0,
        }

        for total in totals:
            data[total["name"]]["total"] = total["total"]
        image = await asyncio.to_thread(RankCardBuilder(data).create_card)

        buf = io.BytesIO()
        image.save(buf, format="png")
        buf.seek(0)

        return Stream(
            content=buf,
            headers={"Content-Disposition": "inline"},
            media_type="image/png",
        )

    @staticmethod
    async def _get_map_totals(conn: asyncpg.Connection) -> list[asyncpg.Record]:
        query = """
            WITH ranges ("range", "name") AS (
                 VALUES  ('[0,0.59)'::numrange, 'Beginner'),
                         ('[0.59,2.35)'::numrange, 'Easy'),
                         ('[2.35,4.12)'::numrange, 'Medium'),
                         ('[4.12,5.88)'::numrange, 'Hard'),
                         ('[5.88,7.65)'::numrange, 'Very Hard'),
                         ('[7.65,9.41)'::numrange, 'Extreme'),
                         ('[9.41,10.0]'::numrange, 'Hell')
            ), map_data AS
            (SELECT avg(difficulty) as difficulty FROM maps m
            LEFT JOIN map_ratings mr ON m.map_code = mr.map_code WHERE m.official = TRUE
                    AND m.archived = FALSE GROUP BY m.map_code)
            SELECT name, count(name) as total FROM map_data md
            INNER JOIN ranges r ON r.range @> md.difficulty
            GROUP BY name
        """
        return await conn.fetch(query)

    @staticmethod
    async def _get_world_record_count(conn: asyncpg.Connection, user_id: int) -> int:
        query = """
            WITH all_records AS (
                SELECT
                    user_id,
                    r.map_code,
                    record,
                    rank() OVER (
                        PARTITION BY r.map_code
                        ORDER BY record
                    ) as pos
                FROM records r
                LEFT JOIN maps m on r.map_code = m.map_code
                WHERE m.official = TRUE AND record < 99999999 AND video IS NOT NULL
            )
            SELECT count(*) FROM all_records WHERE user_id = $1 AND pos = 1
        """
        return await conn.fetchval(query, user_id)

    @staticmethod
    async def _get_maps_count(conn: asyncpg.Connection, user_id: int) -> int:
        query = """
            SELECT count(*)
            FROM maps
            LEFT JOIN map_creators mc ON maps.map_code = mc.map_code
            WHERE user_id = $1 AND official = TRUE
        """
        return await conn.fetchval(query, user_id)

    @staticmethod
    async def _get_playtests_count(conn: asyncpg.Connection, user_id: int) -> int:
        query = "SELECT amount FROM playtest_count WHERE user_id = $1"
        return await conn.fetchval(query, user_id) or 0

    @staticmethod
    async def _get_background_choice(conn: asyncpg.Connection, user_id: int) -> int:
        query = "SELECT value FROM background WHERE user_id = $1"
        return await conn.fetchval(query, user_id) or 1
