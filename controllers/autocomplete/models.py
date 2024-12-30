from __future__ import annotations

import msgspec


class MapBaseAutocompleteResponse(msgspec.Struct):
    name: str


class MapNameAutocompleteResponse(msgspec.Struct):
    map_name: str
    translated_map_name: str


class MapCodeAutocompleteResponse(msgspec.Struct):
    map_code: str


class CreatorAutocompleteResponse(msgspec.Struct):
    name: str
    user_id: int
