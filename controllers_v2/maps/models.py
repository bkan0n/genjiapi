from __future__ import annotations

from typing import Optional, Literal

import msgspec

from utils.utilities import (
    DIFFICULTIES_T,
    MAP_NAME_T,
    MAP_TYPE_T,
    MECHANICS_T,
    RESTRICTIONS_T,
)

STATUS = Literal["official", "playtest"]

class Medals(msgspec.Struct):
    gold: float
    silver: float
    bronze: float

class PlaytestData(msgspec.Struct):
    total_votes: int
    required_votes: int

class MapSearchResponseV2(msgspec.Struct):
    code: str
    category: list[MAP_TYPE_T]
    status: STATUS
    archived: bool
    name: MAP_NAME_T
    checkpoints: int
    difficulty_value: float
    difficulty: DIFFICULTIES_T
    mechanics: list[MECHANICS_T]
    restrictions: list[RESTRICTIONS_T]
    creator_ids: list[int]
    creator_names: list[str]
    creator_discord_tags: list[str]
    quality: Optional[float]
    description: Optional[str]
    guides: Optional[list[str]]
    medals: Optional[Medals]
    playtest: Optional[PlaytestData]

