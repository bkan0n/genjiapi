from __future__ import annotations

from typing import Literal

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

DIFFICULTIES = [
    x for x in filter(lambda y: not ("-" in y or "+" in y), DIFFICULTIES_EXT)
]

def generate_difficulty_ranges(top_level=False) -> dict[str, tuple[float, float]]:
    ranges = {}
    range_length = 10 / len(DIFFICULTIES_EXT)
    cur_range = 0
    for d in DIFFICULTIES_EXT:
        ranges[d] = (round(cur_range, 2), round(cur_range + range_length, 2))
        cur_range += range_length

    if top_level:
        temp_ranges = {}

        for k, v in ranges.items():
            key = k.rstrip(" -").rstrip(" +")
            if key in temp_ranges:
                temp_ranges[key] = (
                    min(temp_ranges[key][0], v[0]),
                    max(temp_ranges[key][1], v[1]),
                )
            else:
                temp_ranges[key] = v

        ranges = temp_ranges

    return ranges

TOP_DIFFICULTIES_RANGES = generate_difficulty_ranges(True)
DIFFICULTIES_RANGES = generate_difficulty_ranges()

def convert_num_to_difficulty(value: float | int) -> str:
    res = "Hell"
    for diff, _range in DIFFICULTIES_RANGES.items():
        if float(_range[0]) <= float(value) + 0.01 < float(_range[1]):
            res = diff
            break
    return res


def wrap_string_with_percent(string: str | None):
    if not string:
        return
    return "%" + string + "%"
