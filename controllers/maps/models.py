from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec
from litestar.openapi.spec import Example

from utils.utilities import ALL_DIFFICULTY_RANGES_MIDPOINT

if TYPE_CHECKING:
    import asyncpg


class MapCompletionStatisticsResponse(msgspec.Struct):
    min: float | None = None
    max: float | None = None
    avg: float | None = None


class MapPerDifficultyResponse(msgspec.Struct):
    difficulty: str
    amount: int


class MapSearchResponse(msgspec.Struct):
    map_name: str
    map_type: list[str]
    map_code: str
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


class MostCompletionsAndQualityResponse(msgspec.Struct):
    map_code: str
    completions: int
    quality: float
    difficulty: str
    ranking: int


class TopCreatorsResponse(msgspec.Struct):
    map_count: int
    name: str
    average_quality: float


class GuidesResponse(msgspec.Struct):
    map_code: str
    url: str
    total_results: int


class MapSubmissionBody(msgspec.Struct):
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
        if all((self.gold, self.silver, self.bronze)) and self.gold < self.silver < self.bronze:
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


class ArchiveMapBody(msgspec.Struct):
    map_code: str

    rabbit_data: dict | None = None

    def __post_init__(self) -> None:
        """Init."""
        self.rabbit_data = {
            "map": {
                "map_code": self.map_code,
            }
        }


map_submission_request_example = [Example(
    summary="Map submission request",
    description="Map submission request",
    value=msgspec.json.encode(MapSubmissionBody(
        map_code="TEST",
        map_type="Classic",
        map_name="Hanamura",
        difficulty="Hell",
        checkpoints=1,
        creator_id=37,
        nickname="TestUser",
    ))
)]