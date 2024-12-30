from __future__ import annotations

import datetime  # noqa: TCH003

import msgspec


class CompletionsResponse(msgspec.Struct):
    map_code: str
    nickname: str
    discord_tag: str
    time: str
    medal: str
    video: str
    total_results: int


class MapRecordProgressionResponse(msgspec.Struct):
    time: float
    inserted_at: datetime.datetime


class PersonalRecordsResponse(msgspec.Struct):
    map_code: str
    nickname: str
    discord_tag: str
    difficulty: str
    time: float
    medal: str
    total_results: int


class TimePlayedPerRankResponse(msgspec.Struct):
    total_seconds: float
    difficulty: str
