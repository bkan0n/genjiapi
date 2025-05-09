from __future__ import annotations

from typing import Literal, Optional

import msgspec

from utils.utilities import (
    DIFFICULTIES_T,
    MAP_NAME_T,
    MAP_TYPE_T,
    MECHANICS_T,
    RESTRICTIONS_T, sanitize_string, DIFFICULTIES_EXT_T,
)

STATUS = Literal["official", "playtest"]

class Medals(msgspec.Struct):
    gold: float
    silver: float
    bronze: float


class PlaytestData(msgspec.Struct):
    total_votes: int | None = None
    required_votes: int | None = None
    thread_id: int | None = None
    participants: list[int] | None = None


class MapSearchResponseV2(msgspec.Struct):
    code: str
    category: list[MAP_TYPE_T]
    status: STATUS
    archived: bool
    name: MAP_NAME_T
    checkpoints: int
    difficulty_value: float
    difficulty: DIFFICULTIES_EXT_T
    mechanics: list[MECHANICS_T]
    restrictions: list[RESTRICTIONS_T]
    creator_ids: list[int]
    creator_names: list[str]
    creator_discord_tags: list[str]
    quality: Optional[float]
    description: Optional[str]
    guides: Optional[list[str]]
    medals: Optional[Medals]

class PlaytestResponse(msgspec.Struct):
    id: int
    code: str
    category: list[MAP_TYPE_T | None]
    status: STATUS
    archived: bool
    name: MAP_NAME_T
    checkpoints: int
    difficulty_value: float | None
    difficulty: DIFFICULTIES_EXT_T | None
    initial_difficulty: DIFFICULTIES_EXT_T | None
    mechanics: list[MECHANICS_T | None]
    restrictions: list[RESTRICTIONS_T | None]
    creator_ids: list[int]
    creator_names: list[str]
    creator_discord_tags: list[str]
    # quality: Optional[float]
    description: Optional[str]
    guides: Optional[list[str | None]]
    # medals: Optional[Medals]
    playtest: Optional[PlaytestData]
    has_participated: Optional[bool] = False
    map_banner_url: str = ""

    def __post_init__(self) -> None:
        """Add map banner url to response dynamically."""
        sanitized_name = sanitize_string(self.name)
        self.map_banner_url = f"https://bkan0n.com/assets/images/map_banners/{sanitized_name}.png"

class Meilisearch(msgspec.Struct):
    hits: list[PlaytestResponse]
    query: str | None
    processing_time_ms: int | None = None
    limit: int | None = None
    offset: int | None = None
    estimated_total_hits: int | None = None



class MapModel(msgspec.Struct):
    code: str
    name: str
    checkpoints: int
    creator_ids: list[int]
    description: str = ""
    guide_url: str = ""
    gold: float = 0
    silver: float = 0
    bronze: float = 0
    category: list[str] = []
    difficulty: str = ""
    mechanics: list[str] = []
    restrictions: list[str] = []
    # These are fetched from the db during the api call
    map_id: int = 0
    creator_names: list[str] = []
    creator_discord_tags: list[str] = []
    
    
class PlaytestMetadata(msgspec.Struct):
    thread_id: int
    map_id: int
    initial_difficulty: str