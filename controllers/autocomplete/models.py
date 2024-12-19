from __future__ import annotations

import msgspec


class MapNameAutocompleteResponse(msgspec.Struct):
    name: str


class MapCodeAutocompleteResponse(msgspec.Struct):
    map_code: str


class CreatorAutocompleteResponse(msgspec.Struct):
    name: str
    user_id: int
