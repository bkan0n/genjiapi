from __future__ import annotations

import re

import msgspec


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

    @staticmethod
    def _sanitize_string(string: str) -> str:
        string = re.sub(r"[^a-zA-Z\s]", "", string)
        string = string.strip().replace(" ", "_")
        return string.lower()

    def _icon_url(self) -> str:
        _sanitized_map_name = self._sanitize_string(self.map_name)
        _lowered_level = self.level.lower()
        return f"assets/mastery/{_sanitized_map_name}_{_lowered_level}.png"


class MultipleMapMasteryData(msgspec.Struct):
    user_id: int
    data: list[MapMasteryData]
