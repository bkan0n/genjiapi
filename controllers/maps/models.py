from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec

from utils.utilities import ALL_DIFFICULTY_RANGES_MIDPOINT

if TYPE_CHECKING:
    import asyncpg


class BaseResponse(msgspec.Struct):
    map_code: str | None = None


class MapCompletionStatisticsResponse(BaseResponse):
    min: float | None = None
    max: float | None = None
    avg: float | None = None


class MapPerDifficultyResponse(BaseResponse, kw_only=True):
    difficulty: str
    amount: int


class MapSearchResponse(BaseResponse, kw_only=True):
    map_name: str
    map_type: list[str]
    official: bool
    archived: bool
    mechanics: list[str]
    restrictions: list[str]
    checkpoints: int
    creators: list[str]
    creators_discord_tag: list[str]
    difficulty: str
    creator_ids: list[int]
    total_results: int
    desc: str | None = None
    guide: list[str] | None = None
    quality: float | None = None
    gold: float | None = None
    silver: float | None = None
    bronze: float | None = None
    playtest_votes: int | None = None
    required_votes: int | None = None
    time: float | None = None
    medal_type: str | None = None


class MostCompletionsAndQualityResponse(BaseResponse, kw_only=True):
    completions: int
    quality: float
    difficulty: str
    ranking: int


class TopCreatorsResponse(msgspec.Struct):
    map_count: int
    name: str
    average_quality: float


class GuidesResponse(BaseResponse, kw_only=True):
    url: str
    total_results: int


class BaseMapBody(msgspec.Struct):
    map_code: str
    map_type: str
    map_name: str
    difficulty: str
    checkpoints: int
    creator_id: int
    nickname: str
    description: str | None = None
    mechanics: list[str] | None = None
    restrictions: list[str] | None = None
    guides: list[str] | None = None
    gold: float | None = None
    silver: float | None = None
    bronze: float | None = None

    rabbit_data: dict | None = None

    def __post_init__(self) -> None:
        """Format data for RabbitMQ to easily process necessary data."""
        self.rabbit_data = {
            "user": {
                "user_id": self.creator_id,
                "nickname": self.nickname,
            },
            "map": {
                "map_code": self.map_code,
                "difficulty": self.difficulty,
                "map_name": self.map_name,
            },
        }

    async def _insert_maps(self, db: asyncpg.Connection) -> None:
        query = """
            INSERT INTO
            maps (map_name, map_type, map_code, "desc", official, checkpoints)
            VALUES ($1, $2, $3, $4, TRUE, $5);
        """
        await db.execute(
            query,
            self.map_name,
            [self.map_type],
            self.map_code,
            self.description,
            self.checkpoints,
        )

    async def _insert_mechanics(self, db: asyncpg.Connection) -> None:
        if not self.mechanics:
            return
        mechanics = [(self.map_code, x) for x in self.mechanics]
        query = """
            INSERT INTO map_mechanics (map_code, mechanic)
            VALUES ($1, $2);
        """
        await db.executemany(query, mechanics)

    async def _insert_restrictions(self, db: asyncpg.Connection) -> None:
        if not self.restrictions:
            return
        restrictions = [(self.map_code, x) for x in self.restrictions]
        query = """
            INSERT INTO map_restrictions (map_code, restriction)
            VALUES ($1, $2);
        """
        await db.executemany(query, restrictions)

    async def _insert_map_creators(self, db: asyncpg.Connection) -> None:
        query = """
            INSERT INTO map_creators (map_code, user_id)
            VALUES ($1, $2);
        """
        await db.execute(
            query,
            self.map_code,
            self.creator_id,
        )

    async def _insert_map_ratings(self, db: asyncpg.Connection) -> None:
        query = """
            INSERT INTO map_ratings (map_code, user_id, difficulty)
            VALUES ($1, $2, $3);
        """

        await db.execute(
            query,
            self.map_code,
            self.creator_id,
            ALL_DIFFICULTY_RANGES_MIDPOINT[self.difficulty],
        )

    async def _insert_guide(self, db: asyncpg.Connection) -> None:
        if not self.guides:
            return
        _guides = [(self.map_code, guide) for guide in self.guides if guide]
        if _guides:
            query = "INSERT INTO guides (map_code, url) VALUES ($1, $2);"
            await db.executemany(query, _guides)

    async def _insert_medals(self, db: asyncpg.Connection) -> None:
        if all((self.gold, self.silver, self.bronze)) and self.gold < self.silver < self.bronze:  # type: ignore
            query = """
                INSERT INTO map_medals (gold, silver, bronze, map_code)
                VALUES ($1, $2, $3, $4);
            """

            await db.execute(
                query,
                self.gold,
                self.silver,
                self.bronze,
                self.map_code,
            )

    async def insert_all(self, db: asyncpg.Connection) -> None:
        """Insert map data into database."""
        async with db.transaction():
            await self._insert_maps(db)
            await self._insert_mechanics(db)
            await self._insert_restrictions(db)
            await self._insert_map_creators(db)
            await self._insert_map_ratings(db)
            await self._insert_guide(db)
            await self._insert_medals(db)


class MapSubmissionBody(BaseMapBody):
    pass


class ArchiveMapBody(BaseResponse):
    rabbit_data: dict | None = None

    def __post_init__(self) -> None:
        """Init."""
        self.rabbit_data = {
            "map": {
                "map_code": self.map_code,
            }
        }


class MapCountsResponse(BaseResponse, kw_only=True):
    map_name: str
    amount: int

query = """

WITH filtered_maps AS (
    SELECT
        m.id,
        m.map_code,
        m.name AS map_name,
        m.map_type,
        m.status,
        m.archived,
        m.description,
        m.checkpoints
    FROM core.maps m
    WHERE
        ($1::text IS NULL OR m.map_code = $1)
        AND ($2::text IS NULL OR m.name = $2)
        AND ($3::text[] IS NULL OR m.map_type && $3)
        AND ($4::text[] IS NULL OR EXISTS (
            SELECT 1 FROM maps.mechanic_links ml
            JOIN maps.mechanics mech ON ml.mechanic_id = mech.id
            WHERE ml.map_id = m.id AND mech.name = ANY($4)
        ))
        AND ($5::text[] IS NULL OR EXISTS (
            SELECT 1 FROM maps.restriction_links rl
            JOIN maps.restrictions re ON rl.restriction_id = re.id
            WHERE rl.map_id = m.id AND re.name = ANY($5)
        ))
        AND ($6::text IS NULL OR EXISTS (
            SELECT 1 FROM maps.creators c
            JOIN core.users u ON c.user_id = u.id
            WHERE c.map_id = m.id AND (u.nickname ILIKE '%' || $6 || '%' OR u.global_name ILIKE '%' || $6 || '%')
        ))
        AND (
            $7::text IS NULL OR EXISTS (
                SELECT 1 FROM playtests.meta pm
                WHERE pm.map_id = m.id AND
                (
                    ($7 = 'Easy' AND pm.initial_difficulty >= 0 AND pm.initial_difficulty < 2.35) OR
                    ($7 = 'Medium' AND pm.initial_difficulty >= 2.35 AND pm.initial_difficulty < 4.12) OR
                    ($7 = 'Hard' AND pm.initial_difficulty >= 4.12 AND pm.initial_difficulty < 5.88) OR
                    ($7 = 'Very Hard' AND pm.initial_difficulty >= 5.88 AND pm.initial_difficulty < 7.65) OR
                    ($7 = 'Extreme' AND pm.initial_difficulty >= 7.65 AND pm.initial_difficulty < 9.41) OR
                    ($7 = 'Hell' AND pm.initial_difficulty >= 9.41 AND pm.initial_difficulty < 10.0)
                )
            )
        )
        AND ($8::numeric IS NULL OR EXISTS (
            SELECT 1 FROM maps.ratings ra
            WHERE ra.map_id = m.id AND ra.quality >= $8
        ))
        AND ($9::boolean IS NULL OR (m.status = 'playtest') = $9)
        AND ($10::boolean IS NULL OR EXISTS (
            SELECT 1 FROM maps.medals md WHERE md.map_id = m.id
        ))
),
map_details AS (
    SELECT
        fm.map_code,
        fm.map_name,
        fm.map_type,
        fm.status = 'official' AS official,
        fm.archived,
        fm.description,
        fm.checkpoints,
        COALESCE(array_agg(DISTINCT mech.name) FILTER (WHERE mech.name IS NOT NULL), ARRAY[]::text[]) AS mechanics,
        COALESCE(array_agg(DISTINCT re.name) FILTER (WHERE re.name IS NOT NULL), ARRAY[]::text[]) AS restrictions,
        COALESCE(array_agg(DISTINCT u.nickname) FILTER (WHERE u.nickname IS NOT NULL), ARRAY[]::text[]) AS creators,
        COALESCE(array_agg(DISTINCT u.global_name) FILTER (WHERE u.global_name IS NOT NULL), ARRAY[]::text[]) AS creators_discord_tag,
        COALESCE(array_agg(DISTINCT u.id) FILTER (WHERE u.id IS NOT NULL), ARRAY[]::bigint[]) AS creator_ids,
        ROUND(AVG(pm.initial_difficulty)::numeric, 2) AS difficulty,
        COUNT(DISTINCT ptv.id) AS playtest_votes,
        COUNT(DISTINCT ra.id) AS total_ratings,
        ROUND(AVG(ra.quality)::numeric, 2) AS quality,
        md.gold,
        md.silver,
        md.bronze,
        COALESCE(array_agg(DISTINCT g.url) FILTER (WHERE g.url IS NOT NULL), ARRAY[]::text[]) AS guide
    FROM filtered_maps fm
    LEFT JOIN maps.mechanic_links ml ON ml.map_id = fm.id
    LEFT JOIN maps.mechanics mech ON ml.mechanic_id = mech.id
    LEFT JOIN maps.restriction_links rl ON rl.map_id = fm.id
    LEFT JOIN maps.restrictions re ON rl.restriction_id = re.id
    LEFT JOIN maps.creators c ON c.map_id = fm.id
    LEFT JOIN core.users u ON c.user_id = u.id
    LEFT JOIN playtests.meta pm ON pm.map_id = fm.id
    LEFT JOIN playtests.votes ptv ON ptv.map_id = fm.id
    LEFT JOIN maps.ratings ra ON ra.map_id = fm.id
    LEFT JOIN maps.medals md ON md.map_id = fm.id
    LEFT JOIN maps.guides g ON g.map_id = fm.id
    GROUP BY fm.id, fm.map_code, fm.map_name, fm.map_type, fm.status, fm.archived, fm.description, fm.checkpoints, md.gold, md.silver, md.bronze
)
SELECT *
FROM map_details
ORDER BY map_name
LIMIT $11 OFFSET $12;



WITH filtered_maps AS (
    SELECT
        m.id,
        m.map_code,
        m.name AS map_name,
        m.map_type,
        m.status,
        m.archived,
        m.description,
        m.checkpoints
    FROM core.maps m
    WHERE
        ($1::text IS NULL OR m.map_code = $1)
        AND ($2::text IS NULL OR m.name ILIKE '%' || $2 || '%')
        AND ($3::text[] IS NULL OR m.map_type && $3)
        AND ($4::text[] IS NULL OR EXISTS (
            SELECT 1 FROM maps.mechanic_links ml
            JOIN maps.mechanics mech ON ml.mechanic_id = mech.id
            WHERE ml.map_id = m.id AND mech.name = ANY($4)
        ))
        AND ($5::text[] IS NULL OR EXISTS (
            SELECT 1 FROM maps.restriction_links rl
            JOIN maps.restrictions re ON rl.restriction_id = re.id
            WHERE rl.map_id = m.id AND re.name = ANY($5)
        ))
        AND ($6::text IS NULL OR EXISTS (
            SELECT 1 FROM maps.creators c
            JOIN core.users u ON c.user_id = u.id
            WHERE c.map_id = m.id AND (u.nickname ILIKE '%' || $6 || '%' OR u.global_name ILIKE '%' || $6 || '%')
        ))
        AND (
            $7::text IS NULL OR EXISTS (
                SELECT 1 FROM playtests.meta pm
                WHERE pm.map_id = m.id AND
                (
                    ($7 = 'Easy' AND pm.initial_difficulty >= 0 AND pm.initial_difficulty < 2.35) OR
                    ($7 = 'Medium' AND pm.initial_difficulty >= 2.35 AND pm.initial_difficulty < 4.12) OR
                    ($7 = 'Hard' AND pm.initial_difficulty >= 4.12 AND pm.initial_difficulty < 5.88) OR
                    ($7 = 'Very Hard' AND pm.initial_difficulty >= 5.88 AND pm.initial_difficulty < 7.65) OR
                    ($7 = 'Extreme' AND pm.initial_difficulty >= 7.65 AND pm.initial_difficulty < 9.41) OR
                    ($7 = 'Hell' AND pm.initial_difficulty >= 9.41 AND pm.initial_difficulty < 10.0)
                )
            )
        )
        AND ($8::numeric IS NULL OR EXISTS (
            SELECT 1 FROM maps.ratings ra
            WHERE ra.map_id = m.id AND ra.quality >= $8
        ))
        AND ($9::boolean IS NULL OR (m.status = 'playtest') = $9)
        AND ($10::boolean IS NULL OR EXISTS (
            SELECT 1 FROM maps.medals md WHERE md.map_id = m.id
        ))
),
mechanics_agg AS (
    SELECT ml.map_id, array_agg(DISTINCT mech.name) AS mechanics
    FROM maps.mechanic_links ml
    JOIN maps.mechanics mech ON mech.id = ml.mechanic_id
    GROUP BY ml.map_id
),
restrictions_agg AS (
    SELECT rl.map_id, array_agg(DISTINCT re.name) AS restrictions
    FROM maps.restriction_links rl
    JOIN maps.restrictions re ON re.id = rl.restriction_id
    GROUP BY rl.map_id
),
creators_agg AS (
    SELECT c.map_id,
           array_agg(DISTINCT u.nickname) AS creators,
           array_agg(DISTINCT u.global_name) AS creators_discord_tag,
           array_agg(DISTINCT u.id) AS creator_ids
    FROM maps.creators c
    JOIN core.users u ON u.id = c.user_id
    GROUP BY c.map_id
),
ratings_agg AS (
    SELECT map_id,
           ROUND(AVG(quality)::numeric, 2) AS quality,
           COUNT(*) AS total_ratings
    FROM maps.ratings
    GROUP BY map_id
),
votes_agg AS (
    SELECT map_id, COUNT(*) AS playtest_votes
    FROM playtests.votes
    GROUP BY map_id
),
meta_agg AS (
    SELECT map_id, ROUND(AVG(initial_difficulty)::numeric, 2) AS difficulty
    FROM playtests.meta
    GROUP BY map_id
),
guides_agg AS (
    SELECT map_id, array_agg(DISTINCT url) AS guide
    FROM maps.guides
    GROUP BY map_id
)
SELECT
    fm.map_code,
    fm.map_name,
    fm.map_type,
    fm.status = 'official' AS official,
    fm.archived,
    fm.description,
    fm.checkpoints,
    COALESCE(mech.mechanics, ARRAY[]::text[]) AS mechanics,
    COALESCE(restr.restrictions, ARRAY[]::text[]) AS restrictions,
    COALESCE(ca.creators, ARRAY[]::text[]) AS creators,
    COALESCE(ca.creators_discord_tag, ARRAY[]::text[]) AS creators_discord_tag,
    COALESCE(ca.creator_ids, ARRAY[]::bigint[]) AS creator_ids,
    ma.difficulty,
    va.playtest_votes,
    ra.total_ratings,
    ra.quality,
    md.gold,
    md.silver,
    md.bronze,
    ga.guide
FROM filtered_maps fm
LEFT JOIN mechanics_agg mech ON mech.map_id = fm.id
LEFT JOIN restrictions_agg restr ON restr.map_id = fm.id
LEFT JOIN creators_agg ca ON ca.map_id = fm.id
LEFT JOIN ratings_agg ra ON ra.map_id = fm.id
LEFT JOIN votes_agg va ON va.map_id = fm.id
LEFT JOIN meta_agg ma ON ma.map_id = fm.id
LEFT JOIN maps.medals md ON md.map_id = fm.id
LEFT JOIN guides_agg ga ON ga.map_id = fm.id
ORDER BY map_name
LIMIT $11 OFFSET $12;


"""