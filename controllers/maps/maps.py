from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

import asyncpg  # noqa: TC002
from litestar import Request, get, post
from litestar.exceptions import HTTPException
from litestar.params import Parameter

from utils import rabbit
from utils.utilities import (
    DIFFICULTIES_T,
    MAP_NAME_T,
    MAP_TYPE_T,
    MECHANICS_T,
    RESTRICTIONS_T,
    TOP_DIFFICULTIES_RANGES,
    convert_num_to_difficulty,
)

from ..root import BaseController
from .models import (
    ArchiveMapBody,
    GuidesResponse,
    MapCompletionStatisticsResponse,
    MapCountsResponse,
    MapPerDifficultyResponse,
    MapSearchResponse,
    MapSubmissionBody,
    MostCompletionsAndQualityResponse,
    TopCreatorsResponse,
)

if TYPE_CHECKING:
    from asyncpg import Connection
    from litestar.datastructures import State


class MapsController(BaseController):
    path = "/maps"
    tags = ["Maps"]

    @get(path="/statistics/completions/{map_code:str}")
    async def get_map_completion_statistics(
        self,
        db_connection: Connection,
        map_code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ],
    ) -> list[MapCompletionStatisticsResponse]:
        """Get the min, max, avg completion time for a particular map code."""
        query = """
            WITH filtered_records AS (
                SELECT
                    *
                FROM records
                WHERE map_code = $1 AND record < 99999999.99 AND verified = TRUE
            )
            SELECT round(min(r.record), 2) AS min, round(max(r.record), 2) AS max, round(avg(r.record), 2) AS avg
            FROM maps m
            LEFT JOIN filtered_records r ON m.map_code = r.map_code
            WHERE $1 = m.map_code
            GROUP BY m.map_code
        """
        rows = await db_connection.fetch(query, map_code)
        return [MapCompletionStatisticsResponse(**row) for row in rows]

    @get(path="/statistics/difficulty")
    async def get_maps_per_difficulty(self, db_connection: Connection) -> list[MapPerDifficultyResponse]:
        """Get the maps per difficulty."""
        query = """
        WITH ranges ("range", "name") AS (
            VALUES  ('[0.0,2.35)'::numrange, 'Easy'),
                    ('[2.35,4.12)'::numrange, 'Medium'),
                    ('[4.12,5.88)'::numrange, 'Hard'),
                    ('[5.88,7.65)'::numrange, 'Very Hard'),
                    ('[7.65,9.41)'::numrange, 'Extreme'),
                    ('[9.41,10.0]'::numrange, 'Hell')
        ),
        map_data AS (
            SELECT avg(mr.difficulty) AS difficulty
            FROM maps m
            LEFT JOIN map_ratings mr ON mr.map_code = m.map_code
            WHERE m.official IS TRUE AND m.archived IS FALSE
            GROUP BY m.map_code
        )
        SELECT
            name AS difficulty,
            count(name) AS amount
        FROM ranges r
        INNER JOIN map_data md ON r.range @> md.difficulty
        GROUP BY name
        ORDER BY
        CASE WHEN name = 'Easy' THEN 1
            WHEN name = 'Medium' THEN 2
            WHEN name = 'Hard' THEN 3
            WHEN name = 'Very Hard' THEN 4
            WHEN name = 'Extreme' THEN 5
            ELSE 6
        END;
        """
        rows = await db_connection.fetch(query)
        return [MapPerDifficultyResponse(**row) for row in rows]

    @get(path="/search")
    async def map_search(
        self,
        db_connection: Connection,
        map_code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ]
        | None = None,
        map_type: list[MAP_TYPE_T] | None = None,
        map_name: MAP_NAME_T | None = None,
        creator: str | None = None,
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
    ) -> list[MapSearchResponse]:
        """Search for maps."""
        logged_in_query = """
            WITH user_completion_data AS (
                SELECT DISTINCT ON (user_id, map_code)
                    map_code,
                    record
                FROM records
                WHERE $14::bigint IS NULL OR user_id = $14
                ORDER BY user_id, map_code, record, inserted_at DESC
            ),
            website_all_maps AS (
                SELECT
                    m.map_name,
                    m.map_type,
                    m.map_code,
                    m."desc",
                    m.official,
                    m.archived,
                    array_agg(DISTINCT mech.mechanic) AS mechanics,
                    array_agg(DISTINCT rest.restriction) AS restrictions,
                    m.checkpoints,
                    coalesce(avg(mr.difficulty), 0::numeric) AS difficulty,
                    coalesce(avg(mr.quality), 0::numeric) AS quality,
                    array_agg(DISTINCT COALESCE(own.username, u.nickname)::text) AS creators,
                    array_agg(DISTINCT u.global_name::text) AS creators_discord_tag,
                    array_agg(DISTINCT mc.user_id) AS creator_ids,
                    mm.gold,
                    mm.silver,
                    mm.bronze
            FROM maps m
            LEFT JOIN map_mechanics mech ON mech.map_code::text = m.map_code::text
            LEFT JOIN map_restrictions rest ON rest.map_code::text = m.map_code::text
            LEFT JOIN map_creators mc ON m.map_code::text = mc.map_code::text
            LEFT JOIN users u ON mc.user_id = u.user_id
            LEFT JOIN user_overwatch_usernames own ON own.user_id = u.user_id AND own.is_primary = true
            LEFT JOIN map_ratings mr ON m.map_code::text = mr.map_code::text
            LEFT JOIN map_medals mm ON m.map_code::text = mm.map_code::text
            GROUP BY m.checkpoints,
                m.map_name,
                m.map_code,
                m."desc",
                m.official,
                m.map_type,
                mm.gold,
                mm.silver,
                mm.bronze,
                m.archived
            ), filtered_maps AS (
                SELECT
                    am.map_name, map_type, am.map_code, am."desc", am.official,
                    am.archived, mechanics, restrictions, am.checkpoints,
                    creators, difficulty, quality, creator_ids, am.gold, am.silver,
                    am.bronze, pa.count AS playtest_votes, pa.required_votes, am.creators_discord_tag
                FROM
                    website_all_maps am
                LEFT JOIN playtest p ON am.map_code = p.map_code AND p.is_author IS TRUE
                LEFT JOIN playtest_avgs pa ON pa.map_code = am.map_code
                WHERE
                    ($1::text IS NULL OR am.map_code = $1)
                    AND ($1::text IS NOT NULL OR ((archived = FALSE)
                    AND (official = $9::bool)
                    AND ($2::text[] IS NULL OR $2 <@ map_type)
                    AND ($3::text IS NULL OR map_name = $3)
                    AND ($4::text[] IS NULL OR $4 <@ mechanics)
                    AND ($11::text[] IS NULL OR $11 <@ restrictions)
                    AND ($5::numeric(10, 2) IS NULL OR $6::numeric(10, 2) IS NULL OR (difficulty >= $5::numeric(10, 2)
                    AND difficulty < $6::numeric(10, 2)))
                    AND ($7::int IS NULL OR quality >= $7)
                    AND ($8::text IS NULL OR $8 ILIKE ANY(creators) OR $8 ILIKE ANY(creators_discord_tag))
                    AND ($10::bool IS FALSE OR (gold IS NOT NULL AND silver IS NOT NULL AND bronze IS NOT NULL))))
                GROUP BY
                    am.map_name, map_type, am.map_code, am."desc", am.official, am.archived, mechanics,
                    restrictions, am.checkpoints, creators, difficulty, quality, creator_ids, am.gold, am.silver,
                    am.bronze, pa.count, pa.required_votes, creators_discord_tag
            )
            SELECT
                fm.*,
                record AS time,
                count(*) OVER() AS total_results,
                CASE
                    WHEN record < fm.gold THEN 'Gold'
                    WHEN record < fm.silver AND record >= fm.gold THEN 'Silver'
                    WHEN record < fm.bronze AND record >= fm.silver THEN 'Bronze'
                END AS medal_type
            FROM filtered_maps fm
            LEFT JOIN user_completion_data ucd ON fm.map_code = ucd.map_code
            WHERE $15::bool IS FALSE OR ucd.map_code IS NULL
            ORDER BY difficulty, quality DESC
            LIMIT $12
            OFFSET $13;
        """
        logged_out_query = """
            WITH website_all_maps AS (
                SELECT
                    m.map_name,
                    map_type,
                    m.map_code,
                    m."desc",
                    m.official,
                    m.archived,
                    array_agg(DISTINCT mech.mechanic) AS mechanics,
                    array_agg(DISTINCT rest.restriction) AS restrictions,
                    m.checkpoints,
                    coalesce(avg(mr.difficulty), 0::numeric) AS difficulty,
                    coalesce(avg(mr.quality), 0::numeric) AS quality,
                    array_agg(DISTINCT COALESCE(own.username, u.nickname)::text) AS creators,
                    array_agg(DISTINCT u.global_name::text) AS creators_discord_tag,
                    array_agg(DISTINCT mc.user_id) AS creator_ids,
                    mm.gold,
                    mm.silver,
                    mm.bronze
            FROM maps m
            LEFT JOIN map_mechanics mech ON mech.map_code::text = m.map_code::text
            LEFT JOIN map_restrictions rest ON rest.map_code::text = m.map_code::text
            LEFT JOIN map_creators mc ON m.map_code::text = mc.map_code::text
            LEFT JOIN users u ON mc.user_id = u.user_id
            LEFT JOIN user_overwatch_usernames own ON own.user_id = u.user_id AND own.is_primary = true
            LEFT JOIN map_ratings mr ON m.map_code::text = mr.map_code::text
            LEFT JOIN map_medals mm ON m.map_code::text = mm.map_code::text
            GROUP BY m.checkpoints,
                m.map_name,
                m.map_code,
                m."desc",
                m.official,
                m.map_type,
                mm.gold,
                mm.silver,
                mm.bronze,
                m.archived
            )
            SELECT
                am.map_name, map_type, am.map_code, am."desc", am.official,
                am.archived, mechanics, restrictions, am.checkpoints,
                creators, difficulty, quality, creator_ids, am.gold, am.silver,
                am.bronze, pa.count AS playtest_votes, pa.required_votes, am.creators_discord_tag,
                count(*) OVER() AS total_results
            FROM
                website_all_maps am
            LEFT JOIN playtest p ON am.map_code = p.map_code AND p.is_author IS TRUE
            LEFT JOIN playtest_avgs pa ON pa.map_code = am.map_code
            WHERE
                ($1::text IS NULL OR am.map_code = $1)
                AND ($1::text IS NOT NULL OR ((archived = FALSE)
                AND (official = $9::bool)
                AND ($2::text[] IS NULL OR $2 <@ map_type)
                AND ($3::text IS NULL OR map_name = $3)
                AND ($4::text[] IS NULL OR $4 <@ mechanics)
                AND ($11::text[] IS NULL OR $11 <@ restrictions)
                AND ($5::numeric(10, 2) IS NULL OR $6::numeric(10, 2) IS NULL OR (difficulty >= $5::numeric(10, 2)
                AND difficulty < $6::numeric(10, 2)))
                AND ($7::int IS NULL OR quality >= $7)
                AND ($8::text IS NULL OR $8 ILIKE ANY(creators) OR $8 ILIKE ANY(creators_discord_tag))
                AND ($10::bool IS FALSE OR (gold IS NOT NULL AND silver IS NOT NULL AND bronze IS NOT NULL))))
            GROUP BY
                am.map_name, map_type, am.map_code, am."desc", am.official, am.archived, mechanics,
                restrictions, am.checkpoints, creators, difficulty, quality, creator_ids, am.gold, am.silver,
                am.bronze, pa.count, pa.required_votes, creators_discord_tag
            ORDER BY difficulty, quality DESC
            LIMIT $12
            OFFSET $13
        """

        ranges = TOP_DIFFICULTIES_RANGES.get(difficulty, None)
        difficulty_low_range = None if ranges is None else ranges[0]
        difficulty_high_range = None if ranges is None else ranges[1]

        offset = (page_number - 1) * page_size

        args = [
            map_code,
            map_type,
            map_name,
            mechanics,
            difficulty_low_range,
            difficulty_high_range,
            minimum_quality,
            creator,
            not only_playtest,
            only_maps_with_medals,
            restrictions,
            page_size,
            offset,
        ]

        if user_id:
            query = logged_in_query
            args += [user_id, ignore_completions]
        else:
            query = logged_out_query

        rows = await db_connection.fetch(query, *args)
        altered_rows = []
        for row in rows:
            altered_row = dict(**row)
            altered_row["difficulty"] = convert_num_to_difficulty(row["difficulty"])
            altered_rows.append(altered_row)
        return [MapSearchResponse(**row) for row in altered_rows]

    @get(path="/popular")
    async def get_popular_maps(self, db_connection: Connection) -> list[MostCompletionsAndQualityResponse]:
        """Get popular maps."""
        query = """
            WITH ranges ("range", "name") AS (
                 VALUES  ('[0.0,2.35)'::numrange, 'Easy'),
                         ('[2.35,4.12)'::numrange, 'Medium'),
                         ('[4.12,5.88)'::numrange, 'Hard'),
                         ('[5.88,7.65)'::numrange, 'Very Hard'),
                         ('[7.65,9.41)'::numrange, 'Extreme'),
                         ('[9.41,10.0]'::numrange, 'Hell')
            ),
            completion_data AS (
                SELECT
                    r.map_code,
                    COUNT(*) AS completions
                FROM records r
                GROUP BY r.map_code
            ),
            rating_data AS (
                SELECT
                    m.map_code,
                    AVG(mr.difficulty) AS difficulty,
                    AVG(mr.quality) AS quality
                FROM maps m
                LEFT JOIN map_ratings mr ON m.map_code = mr.map_code
                GROUP BY m.map_code
            ),
            map_data AS (
                SELECT
                    cd.map_code,
                    cd.completions,
                    rd.difficulty,
                    rd.quality
                FROM completion_data cd
                LEFT JOIN rating_data rd ON cd.map_code = rd.map_code
            ),
            ranked_maps AS (
                SELECT
                    md.map_code,
                    md.completions,
                    round(md.quality, 2) AS quality,
                    r.name AS difficulty,
                    RANK() OVER (PARTITION BY r.name ORDER BY md.completions DESC, md.quality DESC) AS ranking
                FROM ranges r
                INNER JOIN map_data md ON r.range @> md.difficulty
            )
            SELECT *
            FROM ranked_maps
            WHERE ranking <= 5
            ORDER BY
                CASE difficulty
                    WHEN 'Easy' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Hard' THEN 3
                    WHEN 'Very Hard' THEN 4
                    WHEN 'Extreme' THEN 5
                    WHEN 'Hell' THEN 6
                END,
                ranking;
        """
        rows = await db_connection.fetch(query)
        return [MostCompletionsAndQualityResponse(**row) for row in rows]

    @get(path="/popularcreators")
    async def get_popular_creators(self, db_connection: Connection) -> list[TopCreatorsResponse]:
        """Get popular creators."""
        query = """
            WITH map_creator_data AS (
                SELECT m.map_code, mc.user_id, round(avg(quality), 2) AS quality
                FROM maps m
                LEFT JOIN map_creators mc ON m.map_code = mc.map_code
                LEFT JOIN map_ratings mr ON m.map_code = mr.map_code
                WHERE quality IS NOT NULL
                GROUP BY mc.user_id, m.map_code
            ), quality_data AS (
                SELECT
                    count(map_code) AS map_count,
                    coalesce(own.username, u.nickname) AS name,
                    avg(quality) AS average_quality
                FROM map_creator_data mcd
                LEFT JOIN users u ON mcd.user_id = u.user_id
                LEFT JOIN user_overwatch_usernames own ON u.user_id = own.user_id
                GROUP BY mcd.user_id, own.username, u.nickname
                ORDER BY average_quality DESC
            )
            SELECT * FROM quality_data WHERE map_count >= 3
        """
        rows = await db_connection.fetch(query)
        return [TopCreatorsResponse(**row) for row in rows]

    @get(path="/guides")
    async def guides(
        self,
        db_connection: Connection,
        map_code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ]
        | None = None,
    ) -> list[GuidesResponse]:
        """Map guide search."""
        query = """
            SELECT
                map_code,
                url,
                count(*) OVER() AS total_results
            FROM guides
            WHERE ($1::text IS NULL OR map_code = $1::text)
            ORDER BY map_code
        """
        rows = await db_connection.fetch(query, map_code)
        return [GuidesResponse(**row) for row in rows]

    @post(path="/submit")
    async def submit_map(
        self, request: Request, state: State, db_connection: asyncpg.Connection, data: MapSubmissionBody
    ) -> MapSubmissionBody:
        """Submit map."""
        if request.headers.get("x-test-mode"):
            return data
        await data.insert_all(db_connection)
        await rabbit.publish(state, "new_map", data)

    @staticmethod
    async def _remove_map_medal_entries(db: Connection, map_code: str) -> None:
        query = "DELETE FROM map_medals WHERE map_code = $1;"
        await db.execute(query, map_code)

    @staticmethod
    async def _convert_records_to_legacy_completions(db: Connection, map_code: str) -> None:
        query = """
            WITH all_records AS (
                SELECT
                    CASE
                        WHEN verified = TRUE AND record <= gold THEN 'Gold'
                        WHEN verified = TRUE AND record <= silver AND record > gold THEN 'Silver'
                        WHEN verified = TRUE AND record <= bronze AND record > silver THEN 'Bronze'
                        END AS legacy_medal,
                    r.map_code,
                    r.user_id,
                    r.inserted_at
                FROM records r
                LEFT JOIN map_medals mm ON r.map_code = mm.map_code
                WHERE r.map_code = $1 AND legacy IS FALSE
                ORDER BY record
            )
            UPDATE records
            SET
                completion = CASE
                    WHEN all_records.legacy_medal IS NULL THEN TRUE
                    ELSE FALSE
                END,
                legacy = TRUE,
                legacy_medal = all_records.legacy_medal
            FROM all_records
            WHERE
                records.map_code = all_records.map_code AND
                records.user_id = all_records.user_id AND
                records.inserted_at = all_records.inserted_at;
        """
        await db.execute(query, map_code)

    @post(path="/legacy")
    async def bulk_legacy(
        self, request: Request, state: State, db_connection: asyncpg.Connection, data: list[ArchiveMapBody]
    ) -> list[ArchiveMapBody]:
        """Bulk legacy records."""
        if request.headers.get("x-test-mode"):
            return data
        try:
            async with db_connection.transaction():
                for map_ in data:
                    await self._convert_records_to_legacy_completions(db_connection, map_.map_code)
                    await self._remove_map_medal_entries(db_connection, map_.map_code)
        except Exception:
            raise HTTPException(detail="Unable to convert maps to legacy.", status_code=400)
        await rabbit.publish(
            state,
            "bulk_legacy",
            data,
            extra_headers={"x-test-mode": request.headers.get("x-test-mode")},
        )
        return data

    @post(path="/archive")
    async def bulk_archive(
        self, request: Request, state: State, db_connection: asyncpg.Connection, data: list[ArchiveMapBody]
    ) -> list[ArchiveMapBody]:
        """Bulk archive."""
        if request.headers.get("x-test-mode"):
            return data
        args = [(d.map_code, True) for d in data]
        query = "UPDATE maps SET archived = $2 WHERE map_code = $1;"

        try:
            await db_connection.executemany(
                query,
                args,
            )
        except Exception:
            return

        await rabbit.publish(
            state,
            "bulk_archive",
            data,
            extra_headers={"x-test-mode": request.headers.get("x-test-mode")},
        )
        return data

    @post(path="/unarchive")
    async def bulk_unarchive(
        self, request: Request, state: State, db_connection: asyncpg.Connection, data: list[ArchiveMapBody]
    ) -> list[ArchiveMapBody]:
        """Bulk unarchive."""
        if request.headers.get("x-test-mode"):
            return data
        args = [(d.map_code, False) for d in data]
        query = "UPDATE maps SET archived = $2 WHERE map_code = $1;"
        try:
            await db_connection.executemany(
                query,
                args,
            )
        except Exception:
            return

        await rabbit.publish(
            state,
            "bulk_unarchive",
            data,
            extra_headers={"x-test-mode": request.headers.get("x-test-mode")},
        )
        return data

    @get(path="/statistics/counts/unarchived")
    async def get_unarchived_map_count(self, db_connection: asyncpg.Connection) -> list[MapCountsResponse]:
        """Get unarchived map counts."""
        query = """
            SELECT
                name as map_name,
                count(m.map_name) as amount
            FROM all_map_names amn
            LEFT JOIN maps m ON amn.name = m.map_name
            WHERE m.archived IS FALSE
            GROUP BY name
            ORDER BY amount DESC
        """
        rows = await db_connection.fetch(query)
        return [MapCountsResponse(**row) for row in rows]

    @get(path="/statistics/counts/all")
    async def get_total_map_count(self, db_connection: asyncpg.Connection) -> list[MapCountsResponse]:
        """Get the total count of maps per map name regardless of archive status."""
        query = """
            SELECT
                name as map_name,
                count(m.map_name) as amount
            FROM all_map_names amn
            LEFT JOIN maps m ON amn.name = m.map_name
            GROUP BY name
            ORDER BY amount DESC
        """
        rows = await db_connection.fetch(query)
        return [MapCountsResponse(**row) for row in rows]
