from __future__ import annotations

import datetime  # noqa: TCH003

import msgspec


class BaseResponse(msgspec.Struct):
    map_code: str
    nickname: str
    discord_tag: str
    time: float
    medal: str
    total_results: int
    is_world_record: bool


class CompletionsResponse(BaseResponse):
    video: str
    time: str  # Override the type of time to str


class MapRecordProgressionResponse(msgspec.Struct):
    time: float
    inserted_at: datetime.datetime


class PersonalRecordsResponse(BaseResponse):
    difficulty: str


class TimePlayedPerRankResponse(msgspec.Struct):
    total_seconds: float
    difficulty: str
