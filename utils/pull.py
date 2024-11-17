import random

WEIGHTS = {
    "Legendary": {
        "weight": 3,
    },
    "Epic": {
        "weight": 5,
    },
    "Rare": {
        "weight": 25,
    },
    "Common": {
        "weight": 65,
    },
}


def gacha(amount: int) -> list[str]:
    """Pull random rarities."""
    pulls = random.choices(list(WEIGHTS.keys()), [x["weight"] for x in WEIGHTS.values()], k=amount)
    return pulls
