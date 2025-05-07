from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from litestar import Response, get, post
from litestar.params import Parameter

from utils import rabbit

from ..root import BaseControllerV2
from .models import MapModel, MapSearchResponseV2

if TYPE_CHECKING:
    from asyncpg import Connection
    from litestar.datastructures import State

    from utils.utilities import (
        DIFFICULTIES_T,
        MAP_NAME_T,
        MAP_TYPE_T,
        MECHANICS_T,
        RESTRICTIONS_T,
    )

class MapsControllerV2(BaseControllerV2):
    path = "/maps"
    tags = ["v2/Maps"]

    @post(path="/playtests")
    async def create_playtest(
        self,
        db_connection: Connection,
        state: State,
        data: MapModel,
    ) -> Response:

        # aa
        await rabbit.publish(
            state,
            "playtest",
            data,
        )
        return Response(content="Created playtest", status_code=201)

    @get(path="/playtests")
    async def get_playtests(
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
        user_id: int | None = None,
        ignore_playtested: bool = False,
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> list[MapSearchResponseV2]:
        query = """
                SELECT * 
                FROM playtest_search_v2
                WHERE ($1::text IS NULL OR code = $1)
                  AND ($2::text IS NULL OR category <@ $2)
                  AND ($3::text IS NULL OR name = $3)
                  AND ($4::bigint IS NULL OR creator_ids <@ $4)
                  AND ($5::text[] IS NULL OR mechanics <@ $5)
                  AND ($6::text[] IS NULL OR restrictions <@ $6)
                  AND ($7::text IS NULL OR difficulty = $7)
                  AND ($9::bool IS FALSE OR status = 'playtest')
                --AND ($11::bool IS NULL OR user_id IS NULL)
                --AND ($12::bool IS FALSE OR ignore_completions IS TRUE)
                """

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
