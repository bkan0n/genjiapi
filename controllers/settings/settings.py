from __future__ import annotations

import logging

import msgspec
from asyncpg import Connection  # noqa: TC002
from litestar import Request, Response, get, patch
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST

from ..root import BaseController
from .models import Notification, SettingsUpdate

logger = logging.getLogger(__name__)

class SettingsController(BaseController):
    path = "/settings"
    tags = ["Settings"]

    async def get_user_settings(self, connection: Connection, user_id: int) -> int | None:
        """Retrieve the user's settings as a bitmask.

        Args:
            connection (Connection): The database connection.
            user_id (int): The ID of the user.

        Returns:
            int | None: The bitmask representing the user's settings, or None if not found.

        """
        query = "SELECT flags FROM user_notification_settings WHERE user_id = $1;"
        return await connection.fetchval(query, user_id)

    @get("/users/{user_id:int}")
    async def get_settings(self, db_connection: Connection, user_id: int) -> Response:
        """Retrieve the settings for a specific user.

        Args:
            db_connection (Connection): The database connection.
            request (Request): The request object.
            user_id (int): The ID of the user.

        Returns:
            Response: The response containing the user's settings or an error message.

        """
        bitmask = await self.get_user_settings(db_connection, user_id)
        if bitmask is None:
            logger.debug("User %s not found.", user_id)
            bitmask = 0

        notifications = [notif.name for notif in Notification if bitmask & notif]

        logger.debug("User %s settings: %s", user_id, notifications)
        return Response({"user_id": user_id, "notifications": notifications}, status_code=HTTP_200_OK)

    async def update_user_settings(self, connection: Connection, user_id: int, notifications_bitmask: int) -> bool:
        """Update the user settings in the database.

        Args:
            connection (Connection): The database connection.
            user_id (int): The ID of the user.
            notifications_bitmask (int): The bitmask representing the user's notification settings.

        """
        logger.debug(f"Updating user {user_id} settings to bitmask: {notifications_bitmask}")
        query = """
            INSERT INTO user_notification_settings (user_id, flags) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET flags = $2;
        """
        try:
            await connection.execute(query, user_id, notifications_bitmask)
        except Exception:
            return False
        return True

    @patch("/users/{user_id:int}")
    async def update_settings(self, db_connection: Connection, request: SettingsUpdate, user_id: int) -> Response:
        """Update the settings for a specific user.

        Args:
            db_connection (Connection): The database connection.
            request (Request): The request object.
            user_id (int): The ID of the user.

        Returns:
            Response: The response indicating the success or failure of the update.

        """
        try:
            bitmask = request.to_bitmask()
            logger.debug(f"User {user_id} notifications bitmask: {bitmask}")

            if await self.update_user_settings(db_connection, user_id, bitmask):
                return Response({"status": "success", "bitmask": bitmask}, status_code=HTTP_200_OK)
            else:
                return Response({"error": "Update failed"}, status_code=HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            return Response({"error": str(ve)}, status_code=HTTP_400_BAD_REQUEST)
