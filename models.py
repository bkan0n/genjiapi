from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec

if TYPE_CHECKING:
    import datetime


class Map(msgspec.Struct):
    map_name: str
    map_type: list[str]
    map_code: str
    desc: str | None
    official: bool
    checkpoints: int
    archived: bool


class XPLeaderboard(msgspec.Struct):
    nickname: str
    user_id: int
    rank_name: str
    rank_number: int
    xp: int
    world_records: int
    map_count: int
    playtest_votes_count: int


class MapSearchResponse(msgspec.Struct):
    map_name: str
    map_type: list[str]
    map_code: str
    desc: str
    official: bool
    archived: bool
    guide: list[str]
    mechanics: list[str]
    restrictions: list[str]
    checkpoints: int
    creators: list[str]
    creators_discord_tag: list[str]
    difficulty: str
    quality: float
    creator_ids: list[int]
    gold: float
    silver: float
    bronze: float
    playtest_votes: int
    required_votes: int
    total_results: int


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


class CompletionsResponse(msgspec.Struct):
    map_code: str
    nickname: str
    discord_tag: str
    time: str
    medal: str
    video: str
    total_results: int


class GuidesResponse(msgspec.Struct):
    map_code: str
    url: str
    total_results: int


class PersonalRecordsResponse(msgspec.Struct):
    map_code: str
    nickname: str
    discord_tag: str
    difficulty: str
    time: float
    medal: str
    total_results: int


class RewardTypeResponse(msgspec.Struct):
    name: str
    key_type: str
    rarity: str
    type: str


class LootboxKeyTypeResponse(msgspec.Struct):
    name: str


class UserRewardsResponse(msgspec.Struct):
    user_id: int
    earned_at: datetime.datetime
    name: str
    type: str
    rarity: str


class UserLootboxKeysResponse(msgspec.Struct):
    user_id: int
    key_type: str
    earned_at: datetime.datetime


class UserLootboxKeyAmountsResponse(msgspec.Struct):
    key_type: str
    amount: int


class MapPerDifficultyResponse(msgspec.Struct):
    difficulty: str
    amount: int


class XPLeaderboardResponse(msgspec.Struct):
    user_id: int
    xp: int
    raw_tier: int
    normalized_tier: int
    prestige_level: int
    main_tier_name: str
    sub_tier_name: str
    full_tier_name: str


class PlayersPerXPTierResponse(msgspec.Struct):
    tier: str
    amount: int
