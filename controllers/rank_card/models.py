from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import msgspec

from utils.utilities import sanitize_string

if TYPE_CHECKING:
    import asyncpg


async def fetch_map_mastery(db: asyncpg.Connection, user_id: int, map_name: str | None = None) -> list[MapMasteryData]:
    """Fetch map mastery data for given user."""
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
                WHERE ($2::text IS NULL OR amn.name = $2) and amn.name != 'Adlersbrunn'
                ORDER BY amn.name;
            """
    rows = await db.fetch(query, user_id, map_name)
    return [MapMasteryData(**row) for row in rows]


class RankDetail(msgspec.Struct):
    difficulty: str
    completions: int
    gold: int
    silver: int
    bronze: int
    rank_met: bool
    gold_rank_met: bool
    silver_rank_met: bool
    bronze_rank_met: bool


class RankCardDifficultiesData(msgspec.Struct):
    completed: int
    gold: int
    silver: int
    bronze: int
    total: int


class RankCardBadgesData(msgspec.Struct):
    type: str | None
    name: str | None
    url: str = None

    @classmethod
    async def create(
        cls,
        db: asyncpg.Connection,
        user_id: int,
        type_: str | None,
        name: str | None,
    ) -> RankCardBadgesData:
        """Create object asynchronously."""
        inst = cls(type_, name)
        if type_ != "mastery":
            if name:
                inst.url = f"assets/rank_card/spray/{sanitize_string(name)}.webp"
            return inst
        rows = await fetch_map_mastery(db, user_id, name)
        if rows:
            row = rows[0]
            inst.url = row.icon_url
            return inst
        return inst


class RankCardData(msgspec.Struct):
    rank_name: str
    nickname: str
    background: str
    total_maps_created: int
    total_playtests: int
    world_records: int
    difficulties: dict[Literal["Easy", "Medium", "Hard", "Very Hard", "Extreme", "Hell"], RankCardDifficultiesData]
    avatar_skin: str
    avatar_pose: str
    badges: dict[int, RankCardBadgesData]

    xp: int
    community_rank: str
    prestige_level: int

    background_url: str = None
    rank_url: str = None
    avatar_url: str = None

    def __post_init__(self) -> None:
        """Post init."""
        self.background_url = f"assets/rank_card/background/{sanitize_string(self.background)}.webp"
        self.rank_url = f"assets/ranks/{sanitize_string(self.rank_name)}.webp"
        self.avatar_url = (
            f"assets/rank_card/avatar/{sanitize_string(self.avatar_skin)}/{sanitize_string(self.avatar_pose)}.webp"
        )


class RankCardBadgeSettingsBody(msgspec.Struct):
    user_id: int
    badge_name1: str | None = None
    badge_type1: str | None = None
    badge_name2: str | None = None
    badge_type2: str | None = None
    badge_name3: str | None = None
    badge_type3: str | None = None
    badge_name4: str | None = None
    badge_type4: str | None = None
    badge_name5: str | None = None
    badge_type5: str | None = None
    badge_name6: str | None = None
    badge_type6: str | None = None

    badge_url1: str | None = None
    badge_url2: str | None = None
    badge_url3: str | None = None
    badge_url4: str | None = None
    badge_url5: str | None = None
    badge_url6: str | None = None


class MapMasteryData(msgspec.Struct):
    map_name: str
    amount: int
    level: str | None = None
    icon_url: str | None = None

    def __post_init__(self) -> None:
        """Post init."""
        self.level = self._level()
        self.icon_url = self._icon_url()

    def _level(self) -> str:
        thresholds = [
            (0, "Placeholder"),
            (5, "Rookie"),
            (10, "Explorer"),
            (15, "Trailblazer"),
            (20, "Pathfinder"),
            (25, "Specialist"),
            (30, "Prodigy"),
        ]

        icon_name = "Placeholder"
        for threshold, name in thresholds:
            if self.amount >= threshold:
                icon_name = name
        return icon_name

    def _icon_url(self) -> str:
        _sanitized_map_name = sanitize_string(self.map_name)
        _lowered_level = self.level.lower()
        return f"assets/mastery/{_sanitized_map_name}_{_lowered_level}.webp"


class MultipleMapMasteryData(msgspec.Struct):
    user_id: int
    data: list[MapMasteryData]


class BackgroundResponse(msgspec.Struct):
    name: str | None
    url: str = None

    def __post_init__(self) -> None:
        """Post init."""
        if not self.name:
            self.name = "placeholder"
        self.url = f"assets/rank_card/background/{sanitize_string(self.name)}.webp"


class AvatarResponse(msgspec.Struct):
    skin: str | None = "Overwatch 1"
    pose: str | None = "Heroic"

    url: str = None

    def __post_init__(self) -> None:
        """Post init."""
        if not self.skin:
            self.skin = "Overwatch 1"
        if not self.pose:
            self.pose = "Heroic"
        """Post init."""
        self.url = f"assets/rank_card/avatar/{sanitize_string(self.skin)}/{sanitize_string(self.pose)}.webp"
