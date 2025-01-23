import enum
from typing import Type


class Settings(enum.IntFlag):
    NONE = 0
    DM_ON_VERIFICATION = enum.auto()
    DM_ON_SKILL_ROLE_UPDATE = enum.auto()
    DM_ON_LOOTBOX_GAIN = enum.auto()
    PING_ON_XP_GAIN = enum.auto()
    PING_ON_MASTERY = enum.auto()
    PING_ON_COMMUNITY_RANK_UPDATE = enum.auto()

PRETTY_NAMES: dict[Settings, str] = {
    Settings.DM_ON_VERIFICATION: "Direct Message On Verification",
    Settings.DM_ON_SKILL_ROLE_UPDATE: "Direct Message On Skill Role Update",
    Settings.DM_ON_LOOTBOX_GAIN: "Direct Message On Lootbox Gain",
    Settings.PING_ON_XP_GAIN: "Ping On XP Gain",
    Settings.PING_ON_MASTERY: "Ping On Mastery",
    Settings.PING_ON_COMMUNITY_RANK_UPDATE: "Ping On Community Rank Update",
    Settings.NONE: "None"
}


def get_flags_from_value(value: int, enum_cls: Type[enum.IntFlag]) -> list[str]:
    """
    Given an integer, return a list of all IntFlag enum values that compose it.

    Args:
        value (int): The integer to decompose.
        enum_cls (Type[IntFlag]): The IntFlag enum class to use.

    Returns:
        List[IntFlag]: A list of IntFlag members that make up the value.
    """
    flags = [flag for flag in enum_cls if flag & value == flag and flag != 0]
    return [PRETTY_NAMES.get(flag, str(flag)) for flag in flags]


# Example
combined_value = 10
_flags = get_flags_from_value(combined_value, Settings)
print(_flags)