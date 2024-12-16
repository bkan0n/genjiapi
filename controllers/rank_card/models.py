import msgspec


class RankDetail(msgspec.Struct):
    difficulty: str
    completions: int
    gold: int
    silver: int
    bronze: int
    rank_met: bool
    gold_rank_met: bool
    silver_rank_met: bool
    bronze_rank_met: bool
