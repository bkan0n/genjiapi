from __future__ import annotations

import asyncio
import io

import asyncpg  # noqa: TCH002
from litestar import Controller, get, post
from litestar.response import Stream

from utils.utilities import sanitize_string

from .models import (
    AvatarResponse,
    BackgroundResponse,
    RankCardBadgesData,
    RankCardBadgeSettingsBody,
    RankCardData,
    fetch_map_mastery,
)
from .utils import RankCardBuilder, fetch_user_rank_data, find_highest_rank


class RankCardController(Controller):
    path = "/rank_card"
    tags = ["Rank Card"]

    @post(path="/settings/background/{user_id:int}/{background:str}")
    async def set_background(
        self,
        db_connection: asyncpg.Connection,
        user_id: int,
        background: str,
    ) -> BackgroundResponse:
        """Set user background."""
        query = """
            INSERT INTO rank_card_background (name, user_id) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name;
        """
        await db_connection.execute(query, user_id, background)
        return BackgroundResponse(name=background)

    @get(path="/settings/background/{user_id:int}")
    async def get_background(self, db_connection: asyncpg.Connection, user_id: int) -> BackgroundResponse:
        """Get user background."""
        query = "SELECT name FROM rank_card_background WHERE user_id = $1;"
        background = await db_connection.fetchval(query, user_id)
        return BackgroundResponse(name=background)

    @post(path="/settings/avatar/skin/{user_id:int}/{skin:str}")
    async def set_avatar_skin(self, db_connection: asyncpg.Connection, user_id: int, skin: str) -> AvatarResponse:
        """Set user avatar Skin."""
        query = """
                    INSERT INTO rank_card_avatar (skin, user_id) VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET skin = EXCLUDED.skin;
                """
        await db_connection.execute(query, user_id, user_id, skin)
        return AvatarResponse(skin=skin)

    @get(path="/settings/avatar/skin/{user_id:int}")
    async def get_avatar_skin(self, db_connection: asyncpg.Connection, user_id: int) -> AvatarResponse:
        """Get user avatar Skin."""
        query = "SELECT skin FROM rank_card_avatar WHERE user_id = $1;"
        skin = await db_connection.fetchval(query, user_id)
        return AvatarResponse(skin=skin)

    @post(path="/settings/avatar/pose/{user_id:int}/{pose:str}")
    async def set_avatar_pose(self, db_connection: asyncpg.Connection, user_id: int, pose: str) -> AvatarResponse:
        """Set user avatar Skin."""
        query = """
            INSERT INTO rank_card_avatar (pose, user_id) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET pose = EXCLUDED.pose;
        """
        await db_connection.execute(query, user_id, user_id, pose)
        return AvatarResponse(pose=pose)

    @get(path="/settings/avatar/pose/{user_id:int}")
    async def get_avatar_pose(self, db_connection: asyncpg.Connection, user_id: int) -> AvatarResponse:
        """Get user avatar Skin."""
        query = "SELECT pose FROM rank_card_avatar WHERE user_id = $1;"
        pose = await db_connection.fetchval(query, user_id)
        return AvatarResponse(pose=pose)

    @get(path="/settings/badges/{user_id:int}")
    async def fetch_badges_settings(self, db_connection: asyncpg.Connection, user_id: int) -> RankCardBadgeSettingsBody:
        """Fetch current badges settings."""
        query = "SELECT * FROM rank_card_badges WHERE user_id = $1;"
        row = await db_connection.fetchrow(query, user_id)
        if not row:
            return RankCardBadgeSettingsBody(user_id=user_id)
        row_d = {**row}
        for num in range(1, 7):
            type_col = f"badge_type{num}"
            name_col = f"badge_name{num}"
            url_col = f"badge_url{num}"
            if row_d[type_col] == "mastery":
                mastery = await fetch_map_mastery(db_connection, user_id, row_d[name_col])
                if mastery:
                    cur = mastery[0]
                    row_d[url_col] = cur.icon_url
            elif row_d[type_col] == "spray":
                _sanitized = sanitize_string(row_d[name_col])
                row_d[url_col] = f"assets/rank_card/sprays/{_sanitized}.png"

        return RankCardBadgeSettingsBody(**row_d)

    @post(path="/settings/badges/{user_id:int}")
    async def set_badges_settings(
        self,
        db_connection: asyncpg.Connection,
        data: RankCardBadgeSettingsBody,
        user_id: int,
    ) -> RankCardBadgeSettingsBody:
        """Set badges settings."""
        query = """
            INSERT INTO rank_card_badges (
                user_id,
                badge_name1, badge_type1,
                badge_name2, badge_type2,
                badge_name3, badge_type3,
                badge_name4, badge_type4,
                badge_name5, badge_type5,
                badge_name6, badge_type6
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (user_id) DO UPDATE SET
                badge_name1 = excluded.badge_name1,
                badge_type1 = excluded.badge_type1,
                badge_name2 = excluded.badge_name2,
                badge_type2 = excluded.badge_type2,
                badge_name3 = excluded.badge_name3,
                badge_type3 = excluded.badge_type3,
                badge_name4 = excluded.badge_name4,
                badge_type4 = excluded.badge_type4,
                badge_name5 = excluded.badge_name5,
                badge_type5 = excluded.badge_type5,
                badge_name6 = excluded.badge_name6,
                badge_type6 = excluded.badge_type6
        """
        await db_connection.execute(
            query,
            user_id,
            data.badge_name1,
            data.badge_type1,
            data.badge_name2,
            data.badge_type2,
            data.badge_name3,
            data.badge_type3,
            data.badge_name4,
            data.badge_type4,
            data.badge_name5,
            data.badge_type5,
            data.badge_name6,
            data.badge_type6,
        )
        return data

    @get(path="/test/{user_id:int}")
    async def fetch_rank_card_test(
        self,
        db_connection: asyncpg.Connection,
        user_id: int,
    ) -> RankCardData:
        """Fetch rank card test."""
        totals = await self._get_map_totals_no_beginner(db_connection)
        rank_data = await fetch_user_rank_data(db_connection, user_id, True, False)
        world_records = await self._get_world_record_count(db_connection, user_id)
        maps = await self._get_maps_count(db_connection, user_id)
        playtests = await self._get_playtests_count(db_connection, user_id)
        rank = find_highest_rank(rank_data)
        background = await self._get_background_choice(db_connection, user_id)
        nickname = await db_connection.fetchval("SELECT nickname FROM users WHERE user_id = $1;", user_id)
        avatar = await db_connection.fetchrow("SELECT * FROM rank_card_avatar WHERE user_id = $1;", user_id)
        if not avatar:
            avatar = {"skin": "Overwatch 1", "pose": "Heroic"}

        data = {
            "rank_name": rank,
            "nickname": nickname,
            "background": background,
            "total_maps_created": maps,
            "total_playtests": playtests,
            "world_records": world_records,
            "difficulties": {},
            "avatar_skin": avatar["skin"],
            "avatar_pose": avatar["pose"],
            "badges": await self._fetch_rank_card_badge_data(db_connection, user_id),
        }

        for row in rank_data:
            data["difficulties"][row.difficulty] = {
                "completed": row.completions,
                "gold": row.gold,
                "silver": row.silver,
                "bronze": row.bronze,
            }

        for total in totals:
            data["difficulties"][total["name"]]["total"] = total["total"]
        _d = RankCardData(**data)
        return _d

    async def _fetch_rank_card_badge_data(
        self,
        db_connection: asyncpg.Connection,
        user_id: int,
    ) -> dict[int, RankCardBadgesData]:
        query = "SELECT * FROM rank_card_badges WHERE user_id = $1;"
        row = await db_connection.fetchrow(query, user_id)
        if not row:
            row = {}
        return {
            0: await RankCardBadgesData.create(
                db_connection, user_id, row.get("badge_type1", None), row.get("badge_name1", None)
            ),
            1: await RankCardBadgesData.create(
                db_connection, user_id, row.get("badge_type2", None), row.get("badge_name2", None)
            ),
            2: await RankCardBadgesData.create(
                db_connection, user_id, row.get("badge_type3", None), row.get("badge_name3", None)
            ),
            3: await RankCardBadgesData.create(
                db_connection, user_id, row.get("badge_type4", None), row.get("badge_name4", None)
            ),
            4: await RankCardBadgesData.create(
                db_connection, user_id, row.get("badge_type5", None), row.get("badge_name5", None)
            ),
            5: await RankCardBadgesData.create(
                db_connection, user_id, row.get("badge_type6", None), row.get("badge_name6", None)
            ),
        }

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
    async def _get_map_totals_no_beginner(conn: asyncpg.Connection) -> list[asyncpg.Record]:
        query = """
                WITH ranges ("range", "name") AS (
                     VALUES
                             ('[0.0,2.35)'::numrange, 'Easy'),
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
        query = "SELECT name FROM rank_card_background WHERE user_id = $1"
        return await conn.fetchval(query, user_id) or "placeholder"
