from __future__ import annotations

import datetime  # noqa: TCH003

import msgspec

from utils.utilities import sanitize_string


class RewardTypeResponse(msgspec.Struct):
    name: str
    key_type: str
    rarity: str
    type: str

    url: str | None = None

    def __post_init__(self) -> None:
        """Post init."""
        self.url = _reward_url(self.type, self.name)


class LootboxKeyTypeResponse(msgspec.Struct):
    name: str


class UserRewardsResponse(msgspec.Struct):
    user_id: int
    earned_at: datetime.datetime
    name: str
    type: str
    rarity: str

    url: str | None = None

    def __post_init__(self) -> None:
        """Post init."""
        self.url = _reward_url(self.type, self.name)


def _reward_url(type_: str, name: str) -> str:
    sanitized_name = sanitize_string(name)
    if type_ == "spray":
        url = f"assets/rank_card/spray/{sanitized_name}.png"
    elif type_ == "skin":
        url = f"assets/rank_card/avatar/{sanitized_name}/heroic.png"
    elif type_ == "pose":
        url = f"assets/rank_card/avatar/overwatch_1/{sanitized_name}.png"
    elif type_ == "background":
        url = f"assets/rank_card/background/{sanitized_name}.png"
    else:
        url = ""
    return url


class UserLootboxKeyAmountsResponse(msgspec.Struct):
    key_type: str
    amount: int
