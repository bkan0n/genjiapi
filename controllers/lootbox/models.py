from __future__ import annotations

import datetime  # noqa: TCH003

import msgspec


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


class UserLootboxKeyAmountsResponse(msgspec.Struct):
    key_type: str
    amount: int
