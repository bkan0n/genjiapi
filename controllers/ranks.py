from asyncpg import Connection
from litestar import Controller, get

from models import PlayersPerXPTierResponse, XPLeaderboardResponse


class RanksController(Controller):
    path = "/ranks"
    tags = ["Ranks"]

    @get(path="/statistics/xp/players")
    async def get_players_per_xp_tier(self, db_connection: Connection) -> list[PlayersPerXPTierResponse]:
        """Get players per XP tier."""
        query = """
            WITH player_xp AS (
                SELECT
                    x.name AS tier,
                    x.threshold
                FROM users u
                LEFT JOIN xptable xp ON u.user_id = xp.user_id
                LEFT JOIN _metadata_xp_tiers x ON ((coalesce(xp.amount, 0) / 100) % 100) / 5 = x.threshold
            ),
            tier_counts AS (
                SELECT
                    tier,
                    threshold,
                    COUNT(*) AS amount
                FROM player_xp
                GROUP BY tier, threshold
            )
            SELECT
                mxt.name AS tier,
                COALESCE(tc.amount, 0) AS amount  -- Fill missing values with 0
            FROM _metadata_xp_tiers mxt
            LEFT JOIN tier_counts tc ON mxt.name = tc.tier
            ORDER BY mxt.threshold;
        """
        rows = await db_connection.fetch(query)
        return [PlayersPerXPTierResponse(**row) for row in rows]

    @get(path="/statistics/skill/players")
    async def get_players_per_skill_tier(self) -> None:
        """Get players per skill tier."""

    @get(path="/leaderboard/xp")
    async def get_xp_leaderboard(self, db_connection: Connection) -> list[XPLeaderboardResponse]:
        """Get XP Leaderboard."""
        query = """
            SELECT
                u.user_id,
                coalesce(xp.amount, 0) AS xp,
                (coalesce(xp.amount, 0) / 100) AS raw_tier,  -- Integer division for raw tier
                ((coalesce(xp.amount, 0) / 100) % 100) AS normalized_tier,-- Normalized tier, resetting every 100 tiers
                (coalesce(xp.amount, 0) / 100) / 100 AS prestige_level,-- Prestige level based on multiples of 100 tiers
                x.name AS main_tier_name, -- Main tier label without sub-tier levels
                s.name AS sub_tier_name,
                x.name || ' ' || s.name AS full_tier_name -- Sub-tier label
            FROM users u
            LEFT JOIN xptable xp ON u.user_id = xp.user_id
            LEFT JOIN _metadata_xp_tiers x ON (((coalesce(xp.amount, 0) / 100) % 100)) / 5 = x.threshold
            LEFT JOIN _metadata_xp_sub_tiers s ON (coalesce(xp.amount, 0) / 100) % 5 = s.threshold
            ORDER BY xp DESC;
        """
        rows = await db_connection.fetch(query)
        return [XPLeaderboardResponse(**row) for row in rows]
