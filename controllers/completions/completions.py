from typing import Annotated, Literal

from asyncpg import Connection
from litestar import get
from litestar.params import Parameter

from utils.utilities import wrap_string_with_percent

from ..root import BaseController
from .models import (
    CompletionsResponse,
    MapRecordProgressionResponse,
    PersonalRecordsResponse,
    TimePlayedPerRankResponse,
)


class CompletionsController(BaseController):
    path = "/completions"
    tags = ["Completions"]

    @get(path="/progression/{user_id:int}/{map_code:str}")
    async def get_map_record_progression(
        self, db_connection: Connection, user_id: int, map_code: str
    ) -> list[MapRecordProgressionResponse]:
        """Get the progression over time for a user on a particular map."""
        query = """
            SELECT
                record AS time,
                inserted_at
            FROM records
            WHERE user_id = $1
                AND map_code = $2
                AND record < 99999999.99
            ORDER BY inserted_at;
        """
        rows = await db_connection.fetch(query, user_id, map_code)
        return [MapRecordProgressionResponse(**row) for row in rows]

    @get(path="/search")
    async def completions(
        self,
        db_connection: Connection,
        map_code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ]
        | None = None,
        user: str | None = None,
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> list[CompletionsResponse]:
        """Get completions with map_code and user as filters."""
        query = """
            SELECT
                r.map_code,
                record AS time,
                video,
                CASE
                    WHEN record < mm.gold THEN 'Gold'
                    WHEN record < mm.silver AND record >= mm.gold THEN 'Silver'
                    WHEN record < mm.bronze AND record >= mm.silver THEN 'Bronze'
                END AS medal,
                nickname,
                global_name AS discord_tag,
                count(*) OVER() AS total_results
            FROM records r
            LEFT JOIN users u ON u.user_id = r.user_id
            LEFT JOIN user_global_names ugn ON r.user_id = ugn.user_id
            LEFT JOIN map_medals mm ON r.map_code = mm.map_code
            WHERE
                ($1::text IS NULL OR r.map_code = $1) AND
                ($2::text IS NULL OR (nickname ILIKE $2 OR global_name ILIKE $2))
            ORDER BY map_code, record
            LIMIT $3::int
            OFFSET $4::int;
        """
        offset = (page_number - 1) * page_size
        _user = wrap_string_with_percent(user)
        rows = await db_connection.fetch(query, map_code, _user, page_size, offset)
        return [CompletionsResponse(**row) for row in rows]

    @get(path="/personal/{user_id:int}")
    async def personal_records(
        self,
        db_connection: Connection,
        user_id: int,
        map_code: Annotated[
            str,
            Parameter(
                pattern=r"^[A-Z0-9]{4,6}$",
            ),
        ]
        | None = None,
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> list[PersonalRecordsResponse]:
        """Get personal records from a user."""
        query = """
            WITH ranges ("range", "name") AS (
                VALUES
                    ('[0.0,2.35)'::numrange, 'Easy'),
                    ('[2.35,4.12)'::numrange, 'Medium'),
                    ('[4.12,5.88)'::numrange, 'Hard'),
                    ('[5.88,7.65)'::numrange, 'Very Hard'),
                    ('[7.65,9.41)'::numrange, 'Extreme'),
                    ('[9.41,10.0]'::numrange, 'Hell')
            ), c_data AS (
            SELECT
                r.map_code,
                nickname,
                global_name AS discord_tag,
                record AS time,
                avg(mr.difficulty) AS difficulty_value,
                CASE
                    WHEN record < mm.gold THEN 'Gold'
                    WHEN record < mm.silver AND record >= mm.gold THEN 'Silver'
                    WHEN record < mm.bronze AND record >= mm.silver THEN 'Bronze'
                END AS medal,
                count(*) OVER() AS total_results
            FROM records r
            LEFT JOIN users u ON r.user_id = u.user_id
            LEFT JOIN public.user_global_names ugn ON r.user_id = ugn.user_id
            LEFT JOIN map_medals mm ON r.map_code = mm.map_code
            LEFT JOIN map_ratings mr ON r.map_code = mr.map_code
            WHERE
                ($1::text IS NULL OR r.map_code = $1) AND
                r.user_id = $2
            GROUP BY r.map_code, nickname, global_name, record , mm.gold, mm.silver, mm.bronze
            )
            SELECT
                map_code,
                nickname,
                discord_tag,
                time,
                medal,
                total_results,
                name AS difficulty
            FROM ranges r2
            INNER JOIN c_data cd ON r2.range @> cd.difficulty_value
            ORDER BY
            CASE name
                WHEN 'Easy' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Hard' THEN 3
                WHEN 'Very Hard' THEN 4
                WHEN 'Extreme' THEN 5
                WHEN 'Hell' THEN 6
            END, map_code
            LIMIT $3::int
            OFFSET $4::int
        """
        offset = (page_number - 1) * page_size
        rows = await db_connection.fetch(query, map_code, user_id, page_size, offset)
        return [PersonalRecordsResponse(**row) for row in rows]

    @get(path="/statistics/time-played/rank")
    async def get_time_played_per_rank(
        self,
        db_connection: Connection,
    ) -> list[TimePlayedPerRankResponse]:
        """Get the time played per user."""
        query = """
            WITH
                record_sum_by_map_code AS (
                    SELECT
                        sum(record) as total_seconds,
                        map_code
                    FROM records r
                    WHERE verified AND record < 99999999.99
                    GROUP BY map_code
                ),
                ranges AS (
                    SELECT range, name FROM
                    (
                        VALUES
                            ('[0.0,2.35)'::numrange, 'Easy'),
                            ('[2.35,4.12)'::numrange, 'Medium'),
                            ('[4.12,5.88)'::numrange, 'Hard'),
                            ('[5.88,7.65)'::numrange, 'Very Hard'),
                            ('[7.65,9.41)'::numrange, 'Extreme'),
                            ('[9.41,10.0]'::numrange, 'Hell')
                    ) AS ranges("range", "name")
                ),
                map_difficulty_number AS (
                    SELECT
                        map_code,
                        avg(difficulty) AS difficulty
                    FROM map_ratings mr
                    WHERE verified
                    GROUP BY map_code
                ),
                map_difficulty_string AS (
                    SELECT r.name as difficulty, map_code
                    FROM ranges r
                    INNER JOIN map_difficulty_number mdn ON r.range @> mdn.difficulty
                )
            SELECT sum(total_seconds) as total_seconds, difficulty
            FROM record_sum_by_map_code rs
            LEFT JOIN map_difficulty_string mds ON rs.map_code = mds.map_code
            WHERE difficulty IS NOT NULL
            GROUP BY difficulty
            ORDER BY CASE difficulty
                WHEN 'Easy' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Hard' THEN 3
                WHEN 'Very Hard' THEN 4
                WHEN 'Extreme' THEN 5
                WHEN 'Hell' THEN 6
            END;
        """
        rows = await db_connection.fetch(query)
        return [TimePlayedPerRankResponse(**row) for row in rows]
