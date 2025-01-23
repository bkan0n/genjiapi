from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from litestar import Controller, get
from litestar.params import Parameter

from utils.utilities import wrap_string_with_percent

from .models import FullLeaderboardResponse, PlayersPerSkillTierResponse, PlayersPerXPTierResponse

if TYPE_CHECKING:
    from asyncpg import Connection


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
                WHERE xp.amount > 500
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
    async def get_players_per_skill_tier(self, db_connection: Connection) -> list[PlayersPerSkillTierResponse]:
        """Get players per skill tier."""
        query = """
            WITH unioned_records AS (
                (
                    SELECT DISTINCT ON (map_code, user_id)
                        map_code,
                        user_id,
                        record,
                        screenshot,
                        video,
                        verified,
                        message_id,
                        channel_id,
                        completion,
                        NULL AS medal
                    FROM records
                    ORDER BY map_code, user_id, inserted_at DESC
                )
                UNION ALL
                (
                    SELECT DISTINCT ON (map_code, user_id)
                        map_code,
                        user_id,
                        record,
                        screenshot,
                        video,
                        TRUE AS verified,
                        message_id,
                        channel_id,
                        FALSE AS completion,
                        medal
                    FROM legacy_records
                    ORDER BY map_code, user_id, inserted_at DESC
                )
            ),
            ranges AS (
                SELECT range, name FROM
                (
                    VALUES
                        ('[0.0,0.59)'::numrange, 'Beginner', TRUE),
                        ('[0.59,2.35)'::numrange, 'Easy', TRUE),
                        ('[0.0,2.35)'::numrange, 'Easy', FALSE),
                        ('[2.35,4.12)'::numrange, 'Medium', NULL),
                        ('[4.12,5.88)'::numrange, 'Hard', NULL),
                        ('[5.88,7.65)'::numrange, 'Very Hard', NULL),
                        ('[7.65,9.41)'::numrange, 'Extreme', NULL),
                        ('[9.41,10.0]'::numrange, 'Hell', NULL)
                ) AS ranges("range", "name", "includes_beginner")
                WHERE includes_beginner IS NOT FALSE
            ),
            thresholds AS (
                SELECT * FROM (
                    VALUES
                        ('Easy', 10),
                        ('Medium', 10),
                        ('Hard', 10),
                        ('Very Hard', 10),
                        ('Extreme', 7),
                        ('Hell', 3)
                ) AS t(name, threshold)
            ),
            map_data AS (
                SELECT DISTINCT ON (m.map_code, r.user_id)
                    r.user_id,
                    AVG(mr.difficulty) AS difficulty
                FROM unioned_records r
                LEFT JOIN maps m ON r.map_code = m.map_code
                LEFT JOIN map_ratings mr ON m.map_code = mr.map_code
                WHERE m.official = TRUE
                GROUP BY m.map_code, record, r.verified, medal, r.user_id
            ),
            skill_rank_data AS (
                SELECT
                    r.name AS difficulty,
                    md.user_id,
                    COALESCE(SUM(CASE WHEN md.difficulty IS NOT NULL THEN 1 ELSE 0 END), 0) AS completions,
                    COALESCE(SUM(CASE WHEN md.difficulty IS NOT NULL THEN 1 ELSE 0 END), 0) >= t.threshold AS rank_met
                FROM ranges r
                LEFT JOIN map_data md ON r.range @> md.difficulty
                LEFT JOIN thresholds t ON r.name = t.name
                WHERE r.name != 'Beginner'
                GROUP BY r.name, t.threshold, md.user_id
            ),
            first_rank AS (
                SELECT
                    difficulty,
                    user_id,
                    CASE
                        WHEN difficulty = 'Easy' THEN 'Jumper'
                        WHEN difficulty = 'Medium' THEN 'Skilled'
                        WHEN difficulty = 'Hard' THEN 'Pro'
                        WHEN difficulty = 'Very Hard' THEN 'Master'
                        WHEN difficulty = 'Extreme' THEN 'Grandmaster'
                        WHEN difficulty = 'Hell' THEN 'God'
                    END AS rank_name,
                    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY
                        CASE difficulty
                            WHEN 'Easy' THEN 1
                            WHEN 'Medium' THEN 2
                            WHEN 'Hard' THEN 3
                            WHEN 'Very Hard' THEN 4
                            WHEN 'Extreme' THEN 5
                            WHEN 'Hell' THEN 6
                        END DESC
                    ) AS rank_order
                FROM skill_rank_data
                WHERE rank_met
            ),
            all_users AS (
                SELECT DISTINCT user_id FROM users
            ),
            highest_ranks AS (
                SELECT coalesce(fr.rank_name, 'Ninja') AS rank_name
                FROM all_users u
                LEFT JOIN first_rank fr ON u.user_id = fr.user_id AND fr.rank_order = 1
            )
            SELECT count(*) AS amount, rank_name as tier FROM highest_ranks GROUP BY rank_name
            ORDER BY CASE
                        WHEN rank_name = 'Ninja' THEN 7
                        WHEN rank_name = 'Jumper' THEN 6
                        WHEN rank_name = 'Skilled' THEN 5
                        WHEN rank_name = 'Pro' THEN 4
                        WHEN rank_name = 'Master' THEN 3
                        WHEN rank_name = 'Grandmaster' THEN 2
                        WHEN rank_name = 'God' THEN 1
                    END DESC;
        """
        rows = await db_connection.fetch(query)
        return [PlayersPerSkillTierResponse(**row) for row in rows]

    @get(path="/leaderboard/all")
    async def get_full_leaderboard(
        self,
        db_connection: Connection,
        name: str | None = None,
        tier_name: str | None = None,
        skill_rank: str | None = None,
        sort_column: Literal[
            "xp_amount",
            "nickname",
            "prestige_level",
            "wr_count",
            "map_count",
            "playtest_count",
            "discord_tag",
            "skill_rank",
        ] = "xp_amount",
        sort_direction: Literal["asc", "desc"] = "asc",
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
    ) -> list[FullLeaderboardResponse]:
        """Get the full leaderboard."""
        if sort_column == "skill_rank":
            sort_column = """
                CASE
                    WHEN rank_name = 'Ninja' THEN 7
                    WHEN rank_name = 'Jumper' THEN 6
                    WHEN rank_name = 'Skilled' THEN 5
                    WHEN rank_name = 'Pro' THEN 4
                    WHEN rank_name = 'Master' THEN 3
                    WHEN rank_name = 'Grandmaster' THEN 2
                    WHEN rank_name = 'God' THEN 1
                END
            """

        query = f"""
        WITH unioned_records AS (
            (
                SELECT DISTINCT ON (map_code, user_id)
                    map_code,
                    user_id,
                    record,
                    screenshot,
                    video,
                    verified,
                    message_id,
                    channel_id,
                    completion,
                    NULL AS medal
                FROM records
                ORDER BY map_code, user_id, inserted_at DESC
            )
            UNION ALL
            (
                SELECT DISTINCT ON (map_code, user_id)
                    map_code,
                    user_id,
                    record,
                    screenshot,
                    video,
                    TRUE AS verified,
                    message_id,
                    channel_id,
                    FALSE AS completion,
                    medal
                FROM legacy_records
                ORDER BY map_code, user_id, inserted_at DESC
            )
        ),
        ranges AS (
            SELECT range, name FROM
            (
                VALUES
                    ('[0.0,0.59)'::numrange, 'Beginner', TRUE),
                    ('[0.59,2.35)'::numrange, 'Easy', TRUE),
                    ('[0.0,2.35)'::numrange, 'Easy', FALSE),
                    ('[2.35,4.12)'::numrange, 'Medium', NULL),
                    ('[4.12,5.88)'::numrange, 'Hard', NULL),
                    ('[5.88,7.65)'::numrange, 'Very Hard', NULL),
                    ('[7.65,9.41)'::numrange, 'Extreme', NULL),
                    ('[9.41,10.0]'::numrange, 'Hell', NULL)
            ) AS ranges("range", "name", "includes_beginner")
            WHERE includes_beginner IS NOT FALSE
        ),
        thresholds AS (
            SELECT * FROM (
                VALUES
                    ('Easy', 10),
                    ('Medium', 10),
                    ('Hard', 10),
                    ('Very Hard', 10),
                    ('Extreme', 7),
                    ('Hell', 3)
            ) AS t(name, threshold)
        ),
        map_data AS (
            SELECT DISTINCT ON (m.map_code, r.user_id)
                r.user_id,
                AVG(mr.difficulty) AS difficulty
            FROM unioned_records r
            LEFT JOIN maps m ON r.map_code = m.map_code
            LEFT JOIN map_ratings mr ON m.map_code = mr.map_code
            WHERE m.official = TRUE
            GROUP BY m.map_code, record, r.verified, medal, r.user_id
        ),
        skill_rank_data AS (
            SELECT
                r.name AS difficulty,
                md.user_id,
                COALESCE(SUM(CASE WHEN md.difficulty IS NOT NULL THEN 1 ELSE 0 END), 0) AS completions,
                COALESCE(SUM(CASE WHEN md.difficulty IS NOT NULL THEN 1 ELSE 0 END), 0) >= t.threshold AS rank_met
            FROM ranges r
            LEFT JOIN map_data md ON r.range @> md.difficulty
            LEFT JOIN thresholds t ON r.name = t.name
            WHERE r.name != 'Beginner'
            GROUP BY r.name, t.threshold, md.user_id
        ),
        first_rank AS (
            SELECT
                difficulty,
                user_id,
                CASE
                    WHEN difficulty = 'Easy' THEN 'Jumper'
                    WHEN difficulty = 'Medium' THEN 'Skilled'
                    WHEN difficulty = 'Hard' THEN 'Pro'
                    WHEN difficulty = 'Very Hard' THEN 'Master'
                    WHEN difficulty = 'Extreme' THEN 'Grandmaster'
                    WHEN difficulty = 'Hell' THEN 'God'
                END AS rank_name,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY
                    CASE difficulty
                        WHEN 'Easy' THEN 1
                        WHEN 'Medium' THEN 2
                        WHEN 'Hard' THEN 3
                        WHEN 'Very Hard' THEN 4
                        WHEN 'Extreme' THEN 5
                        WHEN 'Hell' THEN 6
                    END DESC
                ) AS rank_order
            FROM skill_rank_data
            WHERE rank_met
        ),
        all_users AS (
            SELECT DISTINCT user_id FROM unioned_records
        ),
        highest_ranks AS (
            SELECT u.user_id, coalesce(fr.rank_name, 'Ninja') AS rank_name
            FROM all_users u
            LEFT JOIN first_rank fr ON u.user_id = fr.user_id AND fr.rank_order = 1
        ),
        ranks AS (
            SELECT
                r.user_id,
                r.map_code,
                rank() OVER (PARTITION BY r.map_code ORDER BY record) AS rank_num
            FROM records r
            JOIN users u ON r.user_id = u.user_id
            WHERE u.user_id > 1000 AND r.record < 99999999 AND r.verified = TRUE
        ),
        world_records AS (
            SELECT
                r.user_id,
                count(r.user_id) AS amount
            FROM ranks r
            WHERE rank_num = 1
            GROUP BY r.user_id
        ),
        map_counts AS (
            SELECT user_id, count(*) AS amount FROM map_creators GROUP BY user_id
        ),
        xp_tiers AS (
            SELECT
                u.user_id,
                nickname,
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
            WHERE u.user_id > 100000
        )
            SELECT
                u.user_id,
                u.nickname AS nickname,
                xp AS xp_amount,
                raw_tier,
                normalized_tier,
                prestige_level,
                full_tier_name AS tier_name,
                coalesce(wr.amount, 0) AS wr_count,
                coalesce(mc.amount, 0) AS map_count,
                coalesce(ptc.amount, 0) AS playtest_count,
                coalesce(ugn.global_name, 'Unknown Username') AS discord_tag,
                coalesce(rank_name, 'Ninja') AS skill_rank,
                COUNT(*) OVER () as total_results
            FROM xp_tiers u
            LEFT JOIN user_global_names ugn ON u.user_id = ugn.user_id
            LEFT JOIN playtest_count ptc ON u.user_id = ptc.user_id
            LEFT JOIN map_counts mc ON u.user_id = mc.user_id
            LEFT JOIN world_records wr ON u.user_id = wr.user_id
            LEFT JOIN highest_ranks hr ON u.user_id = hr.user_id
            WHERE
                ($3::text IS NULL OR (nickname ILIKE $3::text OR ugn.global_name ILIKE $3::text)) AND
                ($4::text IS NULL OR full_tier_name = $4::text) AND
                ($5::text IS NULL OR rank_name = $5::text)
            ORDER BY {sort_column} {sort_direction}
            LIMIT $1::int
            OFFSET $2::int
        """
        offset = (page_number - 1) * page_size
        _name = wrap_string_with_percent(name) if name else name
        rows = await db_connection.fetch(
            query,
            page_size,
            offset,
            _name,
            tier_name,
            skill_rank,
        )
        return [FullLeaderboardResponse(**row) for row in rows]
