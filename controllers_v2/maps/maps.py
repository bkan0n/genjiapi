from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, Optional

import msgspec.json
from httpx import AsyncClient, RequestError, HTTPStatusError
from litestar import Response, get, post
from litestar.params import Parameter

from utils import rabbit
from utils.utilities import (
    DIFFICULTIES_T,  # noqa: TC001
    MAP_NAME_T,  # noqa: TC001
    MAP_TYPE_T,  # noqa: TC001
    MECHANICS_T,  # noqa: TC001
    RESTRICTIONS_T,  # noqa: TC001
)

from ..root import BaseControllerV2
from .models import MapModel, MapSearchResponseV2, PlaytestMetadata, PlaytestResponse, Meilisearch

if TYPE_CHECKING:
    from asyncpg import Connection
    from litestar.datastructures import State


class MapsControllerV2(BaseControllerV2):
    path = "/maps"
    tags = ["v2/Maps"]

    @staticmethod
    async def _insert_core_maps(db_conn: Connection, data: MapModel) -> int:
        query = """
            INSERT INTO core.maps (code, name, category, description, checkpoints, status, archived, difficulty)
            VALUES ($1, $2, $3, $4, $5, 'playtest', false, $6)
            RETURNING id;
        """
        return await db_conn.fetchval(
            query,
            data.code,
            data.name,
            data.category,
            data.description,
            data.checkpoints,
            data.difficulty_value(),
        )

    @staticmethod
    async def _insert_maps_creators(db_conn: Connection, data: MapModel) -> None:
        query = """
            INSERT INTO core.creators (map_id, creator_id, is_primary)
            VALUES ($1, $2, $3)
        """
        args = [(data.map_id, _id, i == 0) for i, _id in enumerate(data.creator_ids)]
        await db_conn.executemany(query, args)

    async def _insert_mechanics(
        self,
        db_conn: Connection,
        data: MapModel,
    ) -> None:
        query = """
            INSERT INTO maps.mechanic_links (map_id, mechanic_id)
            SELECT $1, m.id
            FROM maps.mechanics m
            WHERE m.name = ANY($2::text[])
            ON CONFLICT (map_id, mechanic_id) DO NOTHING;
        """
        await db_conn.execute(query, data.map_id, data.mechanics)

    async def _insert_restrictions(
        self,
        db_conn: Connection,
        data: MapModel,
    ) -> None:
        query = """
            INSERT INTO maps.restriction_links (map_id, restriction_id)
            SELECT $1, r.id
            FROM maps.restrictions r
            WHERE r.name = ANY($2::text[])
            ON CONFLICT (map_id, restriction_id) DO NOTHING;
        """
        await db_conn.execute(query, data.map_id, data.restrictions)

    async def _insert_guide(
        self,
        db_conn: Connection,
        data: MapModel,
    ) -> None:
        query = """
            INSERT INTO maps.guides (map_id, url, user_id)
            VALUES ($1, $2, $3);
        """
        await db_conn.execute(query, data.map_id, data.guide_url, data.creator_ids[0])

    async def _insert_medals(
        self,
        db_conn: Connection,
        data: MapModel,
    ) -> None:
        if not data.gold or not data.silver or not data.bronze:
            return

        query = """
            INSERT INTO maps.medals (map_id, gold, silver, bronze)
            VALUES ($1, $2, $3, $4);
        """
        await db_conn.execute(query, data.map_id, data.gold, data.silver, data.bronze)

    async def _fetch_creator_names(
        self,
        db_conn: Connection,
        data: MapModel,
    ) -> None:
        query = """
            SELECT
                coalesce(ow.username, u.nickname, u.global_name, 'Unknown Username') AS nickname,
                coalesce(global_name, 'Unknown Discord Tag') AS discord_tag
            FROM maps.creators mc
            LEFT JOIN core.users u ON mc.user_id = u.id
            LEFT JOIN user_overwatch_usernames ow ON ow.user_id = mc.user_id
            WHERE map_id = $1;
        """
        rows = await db_conn.fetch(query, data.map_id)
        if not rows:
            return

        data.creator_names = [row["nickname"] for row in rows]
        data.creator_discord_tags = [row["discord_tag"] for row in rows]

    @post(path="/playtests")
    async def create_playtest(
        self,
        db_connection: Connection,
        state: State,
        data: MapModel,
    ) -> Response:

        async with db_connection.transaction():
            map_id = await self._insert_core_maps(db_connection, data)
            data.map_id = map_id
            await self._insert_maps_creators(db_connection, data)
            await self._insert_mechanics(db_connection, data)
            await self._insert_restrictions(db_connection, data)
            await self._insert_guide(db_connection, data)
            await self._insert_medals(db_connection, data)
            await self._fetch_creator_names(db_connection, data)
            await rabbit.publish(
                state,
                "playtest",
                data,
            )
            return Response(content="Created playtest", status_code=201)

    @post(path="/playtests/metadata")
    async def create_playtest_metadata(
        self,
        db_connection: Connection,
        data: PlaytestMetadata,
    ) -> Response:
        query = """
            INSERT INTO playtests.meta (map_id, thread_id, initial_difficulty)
            VALUES ($1, $2, $3);
        """
        await db_connection.execute(
            query,
            data.map_id,
            data.thread_id,
            data.initial_difficulty,
        )
        return Response(content="Created playtest metadata", status_code=201)

    @staticmethod
    def map_participation_filter(value: str | None) -> Optional[bool]:
        if value == "participated":
            return True
        elif value == "not_participated":
            return False
        else:
            return None

    @get(path="/playtests")
    async def get_playtests(
        self,
        db_connection: Connection,
        user_id: int,
        code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ]
        | None = None,
        category: list[MAP_TYPE_T] | None = None,
        name: MAP_NAME_T | None = None,
        creator_id: int | None = None,
        mechanics: list[MECHANICS_T] | None = None,
        restrictions: list[RESTRICTIONS_T] | None = None,
        difficulty: DIFFICULTIES_T | None = None,
        participation_filter: Literal["all", "participated", "not_participated"] = "all",
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> list[PlaytestResponse]:
        """Get all maps that are currently in playtest."""
        query = """
            SELECT *,
                $8 = ANY(participants) AS has_participated,
                count(*) OVER () AS total_results
            FROM playtest_search_v2
            WHERE ($1::text IS NULL OR code = $1)
              AND ($2::text[] IS NULL OR category <@ $2)
              AND ($3::text IS NULL OR name = $3)
              AND ($4::bigint[] IS NULL OR creator_ids <@ $4)
              AND ($5::text[] IS NULL OR mechanics <@ $5)
              AND ($6::text[] IS NULL OR restrictions <@ $6)
              AND ($7::text IS NULL OR difficulty = $7)
              AND (
                  $9::boolean IS NULL OR
                  ($9 = true  AND $8 = ANY(participants)) OR
                  ($9 = false AND NOT $8 = ANY(participants))
              )
              AND status = 'playtest' AND NOT archived
            OFFSET $10
            LIMIT $11;
        """
        rows = await db_connection.fetch(
            query,
            code,
            category,
            name,
            creator_id,
            mechanics,
            restrictions,
            difficulty,
            user_id,
            self.map_participation_filter(participation_filter),
            page_size * (page_number - 1),
            page_size,
        )
        if not rows:
            return []

        return [PlaytestResponse(**row) for row in rows]

    @get(path="/playtests/meilisearch")
    async def get_playtests_meilisearch(
        self,
        db_connection: Connection,
        user_id: int | None = None,
        q: str | None = None,
        code: Annotated[
                  str,
                  Parameter(
                      pattern=r"^[A-Z0-9]{4,6}$",
                  ),
              ]
              | None = None,
        category: list[MAP_TYPE_T] | None = None,
        name: MAP_NAME_T | None = None,
        creator_id: int | None = None,
        mechanics: list[MECHANICS_T] | None = None,
        restrictions: list[RESTRICTIONS_T] | None = None,
        difficulty: DIFFICULTIES_T | None = None,
        participation_filter: Literal["all", "participated", "not_participated"] = "all",
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> Meilisearch:
        """Get all maps that are currently in playtest."""
        try:
            async with AsyncClient() as client:

                response = await client.get("http://meilisearch:7700/indexes/playtest_search/search",
                                            headers={"Content-Type": "application/json"}, params={'q': q})
                response.raise_for_status()
                return msgspec.json.decode(response.content, type=Meilisearch)
        except RequestError as exc:
            return Response({"error": f"Could not connect to Meilisearch: {exc}"}, status_code=502)
        except HTTPStatusError as exc:
            return Response({"error": f"Meilisearch returned an error: {exc}"}, status_code=exc.response.status_code)

    @get(path="/playtests/meilisearch2")
    async def get_playtests_meilisearch2(
        self,
        q: str | None = None,
    ) -> dict:
        """Get all maps that are currently in playtest."""
        try:
            async with AsyncClient() as client:

                response = await client.get("http://meilisearch:7700/indexes/playtest_search/search",
                                            headers={"Content-Type": "application/json"}, params={'q': q})
                response.raise_for_status()
                return response.json()
        except RequestError as exc:
            return Response({"error": f"Could not connect to Meilisearch: {exc}"}, status_code=502)
        except HTTPStatusError as exc:
            return Response({"error": f"Meilisearch returned an error: {exc}"}, status_code=exc.response.status_code)


    @get(path="/")
    async def map_search(
        self,
        db_connection: Connection,
        code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ]
        | None = None,
        category: list[MAP_TYPE_T] | None = None,
        name: MAP_NAME_T | None = None,
        creator_id: int | None = None,
        mechanics: list[MECHANICS_T] | None = None,
        restrictions: list[RESTRICTIONS_T] | None = None,
        difficulty: DIFFICULTIES_T | None = None,
        minimum_quality: Annotated[
            int,
            Parameter(
                ge=1,
                le=6,
            ),
        ]
        | None = None,
        only_playtest: bool | None = False,
        only_maps_with_medals: bool | None = False,
        user_id: int | None = None,
        ignore_completions: bool = False,
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> list[MapSearchResponseV2]:
        query = """
            SELECT * FROM map_search_data_v2
            WHERE 
                ($1::text IS NULL OR code = $1)
                AND ($2::text IS NULL OR category <@ $2)
                AND ($3::text IS NULL OR name = $3)
                AND ($4::bigint IS NULL OR creator_ids <@ $4)
                AND ($5::text[] IS NULL OR mechanics <@ $5)
                AND ($6::text[] IS NULL OR restrictions <@ $6)
                AND ($7::text IS NULL or difficulty = $7)
                AND ($8::int IS NULL OR quality >= $8)
                AND ($9::bool IS FALSE OR status='playtest')
                AND ($10::bool IS FALSE OR medals IS NOT NULL)
                --AND ($11::bool IS NULL OR user_id IS NULL)
                --AND ($12::bool IS FALSE OR ignore_completions IS TRUE)
        """
        rows = await db_connection.fetch(
            query,
            code,
            category,
            name,
            creator_id,
            mechanics,
            restrictions,
            difficulty,
            minimum_quality,
            only_playtest,
            only_maps_with_medals,
        )
        if not rows:
            return []

        return [MapSearchResponseV2(**row) for row in rows]
