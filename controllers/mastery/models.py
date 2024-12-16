from __future__ import annotations

from urllib.parse import quote

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

    def _icon_url(self) -> str:
        path_ = f"/assets/mastery/{self.map_name}/{self.level}.png"
        return quote(path_, safe="=./")


class MultipleMapMasteryData(msgspec.Struct):
    user_id: int
    data: list[MapMasteryData]
