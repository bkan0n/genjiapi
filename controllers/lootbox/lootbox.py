from asyncpg import Connection
from litestar import Request, get, post, put
from litestar.exceptions import HTTPException

from utils.pull import gacha

from ..root import BaseController
from .models import LootboxKeyTypeResponse, RewardTypeResponse, UserLootboxKeyAmountsResponse, UserRewardsResponse


class LootboxController(BaseController):
    path = "/lootbox"
    tags = ["Lootbox"]

    @get(path="/rewards")
    async def view_all_rewards(
        self,
        db_connection: Connection,
        reward_type: str | None = None,
        key_type: str | None = None,
        rarity: str | None = None,
    ) -> list[RewardTypeResponse]:
        """View all possible rewards optionally filtered by reward_type."""
        query = """
            SELECT *
            FROM lootbox_reward_types
            WHERE
                ($1::text IS NULL OR type = $1::text) AND
                ($2::text IS NULL OR key_type = $2::text) AND
                ($3::text IS NULL OR rarity = $3::text)
            ORDER BY key_type, name
        """
        rows = await db_connection.fetch(query, reward_type, key_type, rarity)
        return [RewardTypeResponse(**row) for row in rows]

    @get(path="/keys")
    async def view_all_keys(
        self,
        db_connection: Connection,
        key_type: str | None = None,
    ) -> list[LootboxKeyTypeResponse]:
        """View all possible keys optionally filtered by key_type."""
        query = """
            SELECT *
            FROM lootbox_key_types
            WHERE
                ($1::text IS NULL OR name = $1::text)
            ORDER BY name
        """
        rows = await db_connection.fetch(query, key_type)
        return [LootboxKeyTypeResponse(**row) for row in rows]

    @get(path="/user/{user_id:int}/rewards")
    async def view_user_rewards(
        self,
        db_connection: Connection,
        user_id: int,
        reward_type: str | None = None,
        key_type: str | None = None,
        rarity: str | None = None,
    ) -> list[UserRewardsResponse]:
        """View all rewards a particular user has."""
        query = """
            SELECT DISTINCT ON (rt.name, rt.key_type, rt.type)
                ur.user_id,
                ur.earned_at,
                rt.name,
                rt.type,
                NULL as medal,
                rt.rarity
            FROM lootbox_user_rewards ur
            LEFT JOIN lootbox_reward_types rt ON ur.reward_name = rt.name
                AND ur.reward_type = rt.type
                AND ur.key_type = rt.key_type
            WHERE
                ur.user_id = $1::bigint AND
                ($2::text IS NULL OR rt.type = $2::text) AND
                ($3::text IS NULL OR ur.key_type = $3::text) AND
                ($4::text IS NULL OR rarity = $4::text)

            UNION ALL

            SELECT
                user_id,
                now() as earned_at,
                map_name as name,
                'mastery' as type,
                medal,
                'common' as rarity
            FROM map_mastery
            WHERE user_id = $1::bigint AND medal != 'Placeholder' AND ($2::text IS NULL OR medal = $2::text)
        """
        rows = await db_connection.fetch(query, user_id, reward_type, key_type, rarity)
        return [UserRewardsResponse(**row) for row in rows]

    @get(path="/users/{user_id:int}/keys")
    async def view_user_keys(
        self,
        db_connection: Connection,
        user_id: int,
        key_type: str | None = None,
    ) -> list[UserLootboxKeyAmountsResponse]:
        """View keys owned by a particular user."""
        query = """
            SELECT count(*) as amount, key_type
            FROM lootbox_user_keys
            WHERE
                ($1::bigint = user_id) AND
                ($2::text IS NULL OR key_type = $2::text)
            GROUP BY key_type
        """

        rows = await db_connection.fetch(query, user_id, key_type)
        return [UserLootboxKeyAmountsResponse(**row) for row in rows]

    @staticmethod
    async def _get_user_key_count(conn: Connection, user_id: int, key_type: str) -> int:
        query = "SELECT count(*) as keys FROM lootbox_user_keys WHERE key_type = $1 AND user_id = $2"
        return await conn.fetchval(query, key_type, user_id)

    @staticmethod
    async def _use_user_key(conn: Connection, user_id: int, key_type: str) -> None:
        query = """
            DELETE FROM lootbox_user_keys
            WHERE earned_at = (
                SELECT MIN(earned_at)
                FROM lootbox_user_keys
                WHERE user_id = $1::bigint AND key_type = $2::text
            ) AND user_id = $1::bigint AND key_type = $2::text;
        """
        await conn.execute(query, user_id, key_type)

    @get(path="/users/{user_id:int}/keys/{key_type:str}")
    async def get_random_items(
        self,
        request: Request,
        db_connection: Connection,
        user_id: int,
        key_type: str,
        amount: int = 3,
    ) -> list[RewardTypeResponse]:
        """Get random items."""
        key_count = await self._get_user_key_count(db_connection, user_id, key_type)
        if key_count <= 0 and not request.headers.get("x-test-mode"):
            raise HTTPException(detail="User does not have enough keys for this action.", status_code=400)

        rarities = gacha(amount)
        items = []
        query = """
            WITH selected_rewards AS (
                SELECT *
                FROM lootbox_reward_types
                WHERE
                    rarity = $1::text AND
                    key_type = $2::text
                ORDER BY random()
                LIMIT 1
            )
            SELECT
                sr.*,
                EXISTS(
                    SELECT 1
                    FROM lootbox_user_rewards ur
                    WHERE ur.user_id = $3::bigint AND
                        ur.reward_name = sr.name AND
                        ur.reward_type = sr.type AND
                        ur.key_type = $2::text
                ) AS duplicate,
                CASE
                    WHEN EXISTS(
                        SELECT 1
                        FROM lootbox_user_rewards ur
                        WHERE ur.user_id = $3::bigint AND
                            ur.reward_name = sr.name AND
                            ur.reward_type = sr.type AND
                            ur.key_type = $2::text
                    )
                    THEN CASE
                        WHEN sr.rarity = 'common' THEN 100
                        WHEN sr.rarity = 'rare' THEN 250
                        WHEN sr.rarity = 'epic' THEN 500
                        WHEN sr.rarity = 'legendary' THEN 1000
                        ELSE 0
                    END
                ELSE 0
                END AS coin_amount
            FROM selected_rewards sr;
        """
        for rarity in rarities:
            reward = await db_connection.fetchrow(query, rarity.lower(), key_type, user_id)
            items.append(reward)

        return [RewardTypeResponse(**row) for row in items]

    @post(path="/users/{user_id:int}/{key_type:str}/{reward_type:str}/{reward_name:str}")
    async def grant_reward_to_user(
        self,
        request: Request,
        db_connection: Connection,
        user_id: int,
        key_type: str,
        reward_type: str,
        reward_name: str,
    ) -> None:
        """Grant reward to user."""
        key_count = await self._get_user_key_count(db_connection, user_id, key_type)
        if key_count <= 0 and not request.headers.get("x-test-mode"):
            raise HTTPException(detail="User does not have enough keys for this action.", status_code=400)

        # TODO: Remove this check once website is set up for this
        query = """
            SELECT rt.rarity
            FROM lootbox_user_rewards ur
            JOIN lootbox_reward_types rt ON ur.reward_name = rt.name
                AND ur.reward_type = rt.type
                AND ur.key_type = rt.key_type
            WHERE ur.user_id = $1::bigint AND
              ur.reward_type = $2::text AND
              ur.key_type = $3::text AND
              ur.reward_name = $4::text
        """
        is_duplicate = await db_connection.fetchval(query, user_id, reward_type, key_type, reward_name)
        if is_duplicate:
            reward_type = "coins"
            coin_convert = {
                "common": 100,
                "rare": 250,
                "epic": 500,
                "legendary": 1000,
            }
            reward_name = str(coin_convert[is_duplicate])

        async with db_connection.transaction():
            if not request.headers.get("x-test-mode"):
                await self._use_user_key(db_connection, user_id, key_type)
            if reward_type != "coins":
                query = """
                    INSERT INTO lootbox_user_rewards (user_id, reward_type, key_type, reward_name)
                    VALUES ($1, $2, $3, $4)
                """
                await db_connection.execute(query, user_id, reward_type, key_type, reward_name)
            else:
                query = """
                    INSERT INTO users (user_id, coins) VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET coins = users.coins + excluded.coins
                """
                await db_connection.execute(query, user_id, int(reward_name))

    @post(path="/user/{user_id:int}/keys/{key_type:str}")
    async def grant_key_to_user(self, db_connection: Connection, user_id: int, key_type: str) -> None:
        """Grant key to user."""
        query = """
            INSERT INTO lootbox_user_keys (user_id, key_type) VALUES ($1, $2)
        """
        await db_connection.execute(query, user_id, key_type)

    @post(path="/users/debug/{user_id:int}/{key_type:str}/{reward_type:str}/{reward_name:str}")
    async def debug_grant_reward_no_key(
        self,
        db_connection: Connection,
        user_id: int,
        key_type: str,
        reward_type: str,
        reward_name: str,
    ) -> None:
        """DEBUG ONLY: Grant reward to user without key."""
        if reward_type != "coins":
            query = """
                INSERT INTO lootbox_user_rewards (user_id, reward_type, key_type, reward_name)
                VALUES ($1, $2, $3, $4)
            """
            await db_connection.execute(query, user_id, reward_type, key_type, reward_name)
        else:
            query = """
                INSERT INTO users (user_id, coins) VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET coins = users.coins + excluded.coins
            """
            await db_connection.execute(query, user_id, int(reward_name))

    @put(path="/keys/{key_type:str}")
    async def set_active_key(self, db_connection: Connection, request: Request, key_type: str) -> None:
        """Set active key."""
        if request.headers.get("x-test-mode"):
            return
        query = "UPDATE lootbox_active_key SET key = $1;"
        await db_connection.execute(query, key_type)

    @post(path="/users/{user_id:int}/coins")
    async def get_user_coins_amount(
        self,
        db_connection: Connection,
        user_id: int,
    ) -> int:
        """Get the amount of coins a user has."""
        query = "SELECT coins FROM users WHERE user_id = $1;"
        amount = await db_connection.fetchval(query, user_id)
        if amount is None:
            return 0
        return amount
