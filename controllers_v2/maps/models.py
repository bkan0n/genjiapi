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


DIFFICULTIES_T = Literal[
    "Beginner",
    "Easy",
    "Medium",
    "Hard",
    "Very Hard",
    "Extreme",
    "Hell",
]

MECHANICS_T = Literal[
    "Edge Climb",
    "Bhop",
    "Crouch Edge",
    "Save Climb",
    "Bhop First",
    "High Edge",
    "Distance Edge",
    "Quick Climb",
    "Slide",
    "Stall",
    "Dash",
    "Ultimate",
    "Emote Save Bhop",
    "Death Bhop",
    "Triple Jump",
    "Multi Climb",
    "Vertical Multi Climb",
    "Create Bhop",
    "Standing Create Bhop",
]

RESTRICTIONS_T = Literal[
    "Dash Start",
    "Triple Jump",
    "Emote Save Bhop ",
    "Death Bhop",
    "Multi Climb",
    "Standing Create Bhop",
    "Create Bhop",
    "Wall Climb",
]

MAP_TYPE_T = Literal[
    "Classic",
    "Increasing Difficulty",
    "Tournament",
    "Aim Parkour (Hanzo)",
    "Practice",
]

MAP_NAME_T = Literal[
    "Ayutthaya",
    "Black Forest",
    "Blizzard World",
    "Busan",
    "Castillo",
    "Chateau Guillard",
    "Circuit Royal",
    "Colosseo",
    "Dorado",
    "Ecopoint: Antarctica",
    "Eichenwalde",
    "Esperanca",
    "Hanamura",
    "Havana",
    "Hollywood",
    "Horizon Lunar Colony",
    "Ilios",
    "Junkertown",
    "Kanezaka",
    "King's Row",
    "Lijiang Tower",
    "Malevento",
    "Midtown",
    "Necropolis",
    "Nepal",
    "New Queen Street",
    "Numbani",
    "Oasis",
    "Paraiso",
    "Paris",
    "Petra",
    "Practice Range",
    "Rialto",
    "Route 66",
    "Temple of Anubis",
    "Volskaya Industries",
    "Watchpoint: Gibraltar",
    "Workshop Chamber",
    "Workshop Expanse",
    "Workshop Green Screen",
    "Workshop Island",
    "Framework",
    "Tools",
    "Shambali",
    "Chateau Guillard (Halloween)",
    "Eichenwalde (Halloween)",
    "Hollywood (Halloween)",
    "Black Forest (Winter)",
    "Blizzard World (Winter)",
    "Ecopoint: Antarctica (Winter)",
    "Hanamura (Winter)",
    "King's Row (Winter)",
    "Busan (Lunar New Year)",
    "Lijiang Tower (Lunar New Year)",
    "Antarctic Peninsula",
    "Suravasa",
    "New Junk City",
    "Samoa",
    "Hanaoka",
    "Runasapi",
    "Throne of Anubis",
]

DIFFICULTIES_EXT = [
    "Beginner",
    "Easy -",
    "Easy",
    "Easy +",
    "Medium -",
    "Medium",
    "Medium +",
    "Hard -",
    "Hard",
    "Hard +",
    "Very Hard -",
    "Very Hard",
    "Very Hard +",
    "Extreme -",
    "Extreme",
    "Extreme +",
    "Hell",
]

DIFFICULTIES = list(filter(lambda y: not ("-" in y or "+" in y), DIFFICULTIES_EXT))


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