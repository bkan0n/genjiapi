from __future__ import annotations

import msgspec


class MapCompletionStatisticsResponse(msgspec.Struct):
    min: float | None = None
    max: float | None = None
    avg: float | None = None


class MapPerDifficultyResponse(msgspec.Struct):
    difficulty: str
    amount: int


class MapSearchResponse(msgspec.Struct):
    map_name: str
    map_type: list[str]
    map_code: str
    official: bool
    archived: bool
    mechanics: list[str]
    restrictions: list[str]
    checkpoints: int
    creators: list[str]
    creators_discord_tag: list[str]
    difficulty: str
    creator_ids: list[int]
    total_results: int
    desc: str | None = None
    guide: list[str] | None = None
    quality: float | None = None
    gold: float | None = None
    silver: float | None = None
    bronze: float | None = None
    playtest_votes: int | None = None
    required_votes: int | None = None
    time: float | None = None
    medal_type: str | None = None


class MostCompletionsAndQualityResponse(msgspec.Struct):
    map_code: str
    completions: int
    quality: float
    difficulty: str
    ranking: int


class TopCreatorsResponse(msgspec.Struct):
    map_count: int
    name: str
    average_quality: float


class GuidesResponse(msgspec.Struct):
    map_code: str
    url: str
    total_results: int


class MapSubmissionBody(msgspec.Struct):
    map_code: str
    map_type: str
    map_name: str
    difficulty: str
    checkpoints: int
    creator_id: int
    mechanics: list[str] | None = None
    restrictions: list[str] | None = None
    description: str | None = None
    guide: str | None = None
    gold: float | None = None
    silver: float | None = None
    bronze: float | None = None
