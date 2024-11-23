from __future__ import annotations

import msgspec


class PlayersPerXPTierResponse(msgspec.Struct):
    tier: str
    amount: int


class FullLeaderboardResponse(msgspec.Struct):
    user_id: int
    nickname: str
    xp_amount: int
    raw_tier: int
    normalized_tier: int
    prestige_level: int
    tier_name: str
    wr_count: int
    map_count: int
    playtest_count: int
    discord_tag: str
    skill_rank: str
    total_results: int


class PlayersPerSkillTierResponse(msgspec.Struct):
    tier: str
    amount: int
