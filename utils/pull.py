import random

WEIGHTS = {
    "Legendary" : {
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
    }
}


def gacha(amount: int) -> list[str]:
    pulls = random.choices(
        list(WEIGHTS.keys()),
        list(map(lambda x: x["weight"], WEIGHTS.values())),
        k=amount
    )
    return pulls
