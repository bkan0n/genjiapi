import enum
import re
from typing import Literal

from msgspec import Struct

NOTIFICATION_TYPES = Literal[
    "NONE",
    "DM_ON_VERIFICATION",
    "DM_ON_SKILL_ROLE_UPDATE",
    "DM_ON_LOOTBOX_GAIN",
    "PING_ON_XP_GAIN",
    "PING_ON_MASTERY",
    "PING_ON_COMMUNITY_RANK_UPDATE",
]

USERNAME_REGEX = re.compile(r'^(?P<name>[^#]+)(?:#(?P<tag>\d+))?$')

class Notification(enum.IntFlag):
    NONE = 0
    DM_ON_VERIFICATION = enum.auto()
    DM_ON_SKILL_ROLE_UPDATE = enum.auto()
    DM_ON_LOOTBOX_GAIN = enum.auto()
    PING_ON_XP_GAIN = enum.auto()
    PING_ON_MASTERY = enum.auto()
    PING_ON_COMMUNITY_RANK_UPDATE = enum.auto()


class SettingsUpdate(Struct):
    notifications: list[NOTIFICATION_TYPES]

    def __post_init__(self) -> None:
        """Post-initialization processing to validate notification names."""
        valid_names = {flag.name for flag in Notification if flag.name is not None}
        for name in self.notifications:
            if name not in valid_names:
                raise ValueError(
                    f"Invalid notification type: {name}. "
                    f"Valid types: {', '.join(valid_names)}"
                )

    def to_bitmask(self) -> int:
        """Convert the list of notification names to a bitmask."""
        mask = Notification(0)
        for name in self.notifications:
            if name == "NONE":
                return 0
            mask |= Notification[name]
        return mask.value



class OverwatchUsernameItem(Struct):
    username: str
    primary: bool = False

    def __post_init__(self) -> None:
        """Post-initialization processing to validate the username format."""
        if not USERNAME_REGEX.match(self.username):
            raise ValueError(
                f"Invalid Overwatch username format: '{self.username}'. "
                "Expected format like 'nebula#11571' or 'nebula'."
            )

class OverwatchUsernamesUpdate(Struct):
    usernames: list[OverwatchUsernameItem]

    def __post_init__(self) -> None:
        """Post-initialization processing to enforce primary username constraints."""
        primary_count = sum(1 for item in self.usernames if item.primary)
        if primary_count > 1:
            raise ValueError("Only one Overwatch username can be primary.")
        if primary_count == 0 and self.usernames:
            raise ValueError("One Overwatch username must be designated as primary.")


class OverwatchUsernamesResponse(OverwatchUsernamesUpdate):
    user_id: int

