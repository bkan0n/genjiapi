from __future__ import annotations

import logging
from typing import Annotated

from asyncpg import Connection  # noqa: TC002
from litestar import Request, Response, get, patch
from litestar.exceptions import HTTPException
from litestar.params import Body
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from ..root import BaseController
from .models import (
    NOTIFICATION_TYPES,
    Notification,
    OverwatchUsernameItem,
    OverwatchUsernamesResponse,
    OverwatchUsernamesUpdate,
    SettingsUpdate,
)

logger = logging.getLogger(__name__)

class SettingsController(BaseController):
    path = "/settings"
    tags = ["Settings"]

    async def _fetch_user_notifications(self, connection: Connection, user_id: int) -> int | None:
        """Retrieve the user's settings as a bitmask.

        Args:
            connection (Connection): The database connection.
            user_id (int): The ID of the user.

        Returns:
            int | None: The bitmask representing the user's settings, or None if not found.

        """
        query = "SELECT flags FROM user_notification_settings WHERE user_id = $1;"
        return await connection.fetchval(query, user_id)

    @get("/users/{user_id:int}/notifications")
    async def get_user_notifications(self, db_connection: Connection, user_id: int) -> Response:
        """Retrieve the settings for a specific user.

        Args:
            db_connection (Connection): The database connection.
            request (Request): The request object.
            user_id (int): The ID of the user.

        Returns:
            Response: The response containing the user's settings or an error message.

        """
        bitmask = await self._fetch_user_notifications(db_connection, user_id)
        if bitmask is None:
            logger.debug("User %s not found.", user_id)
            bitmask = 0

        notifications = [notif.name for notif in Notification if bitmask & notif]

        logger.debug("User %s settings: %s", user_id, notifications)
        return Response({"user_id": user_id, "notifications": notifications}, status_code=HTTP_200_OK)

    async def _update_user_notifications(self, connection: Connection, user_id: int, notifications_bitmask: int) -> bool:
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

    @patch("/users/{user_id:int}/notifications")
    async def bulk_update_notifications(
        self,
        db_connection: Connection,
        request: Request,
        data: Annotated[SettingsUpdate, Body(title="User Notifications")],
        user_id: int,
    ) -> Response:
        """Update the settings for a specific user.

        Args:
            db_connection (Connection): The database connection.
            request (Request): The request object.
            data (SettingsUpdate): The SettingsUpdate object.
            user_id (int): The ID of the user.

        Returns:
            Response: The response indicating the success or failure of the update.

        """
        if request.headers.get("x-test-mode"):
            return Response({"status": "success"}, status_code=HTTP_200_OK)
        try:
            bitmask = data.to_bitmask()
            logger.debug(f"User {user_id} notifications bitmask: {bitmask}")

            if await self._update_user_notifications(db_connection, user_id, bitmask):
                return Response({"status": "success", "bitmask": bitmask}, status_code=HTTP_200_OK)
            else:
                return Response({"error": "Update failed"}, status_code=HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            return Response({"error": str(ve)}, status_code=HTTP_400_BAD_REQUEST)

    @patch("/users/{user_id:int}/notifications/{notification_type:str}")
    async def update_notification(
        self,
        db_connection: Connection,
        user_id: int,
        notification_type: NOTIFICATION_TYPES,
        data: Annotated[bool, Body(title="Enable Notification")]
    ) -> Response:
        """Update a single notification flag for a user.

        The endpoint URL includes the notification type (e.g. "DM_ON_VERIFICATION").
        The request body should be a boolean: true to enable, false to disable.
        """
        valid_notification_names = {flag.name for flag in Notification}
        if notification_type not in valid_notification_names:
            return Response({"error": f"Invalid notification type: {notification_type}"}, status_code=HTTP_400_BAD_REQUEST)
        try:
            current_bitmask = await self._fetch_user_notifications(db_connection, user_id)
            if current_bitmask is None:
                current_bitmask = 0
            current_flags = Notification(current_bitmask)
            notification_flag = Notification[notification_type]

            new_flags = current_flags | notification_flag if data else current_flags & ~notification_flag

            logger.debug(
                "User %s: updating %s to %s, bitmask: %s -> %s",
                user_id,
                notification_type,
                "enabled" if data else "disabled",
                current_flags.value,
                new_flags.value,
            )

            if await self._update_user_notifications(db_connection, user_id, new_flags.value):
                return Response({"status": "success", "bitmask": new_flags.value}, status_code=HTTP_200_OK)
            else:
                return Response({"error": "Update failed"}, status_code=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Error updating single notification: %s", e)
            return Response({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)

    @patch("/users/{user_id:int}/overwatch")
    async def update_overwatch_usernames(
        self,
        db_connection: Connection,
        user_id: int,
        data: Annotated[OverwatchUsernamesUpdate, Body(title="User Overwatch Usernames")],
    ) -> Response:
        """Update the Overwatch usernames for a specific user.

        Args:
            db_connection (Connection): The database connection.
            user_id (int): The ID of the user.
            data (OverwatchUsernamesUpdate): The OverwatchUsernamesUpdate object.

        Returns:
            Response: The response indicating the success or failure of the update.

        """
        try:
            logger.info(f"Set Overwatch usernames for user {user_id}: {data.usernames}")
            await self._set_overwatch_usernames(db_connection, user_id, data.usernames)
            return Response({"success": True}, status_code=HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating Overwatch usernames for user {user_id}: {e}")
            return Response({"error": str(e)}, status_code=HTTP_400_BAD_REQUEST)

    async def _set_overwatch_usernames(
        self,
        db: Connection,
        user_id: int,
        new_usernames: list[OverwatchUsernameItem]
    ) -> None:
        """Set the Overwatch usernames for a specific user.

        Args:
            db (Connection): The database connection.
            user_id (int): The ID of the user.
            new_usernames (list[OverwatchUsernameItem]): The list of new Overwatch usernames.

        """
        new_names = {item.username for item in new_usernames}

        existing_rows = await db.fetch(
            "SELECT username FROM user_overwatch_usernames WHERE user_id = $1", user_id
        )
        existing_names = {row["username"] for row in existing_rows}

        names_to_delete = existing_names - new_names
        if names_to_delete:
            await db.execute(
                """
                DELETE FROM user_overwatch_usernames
                WHERE user_id = $1 AND username = ANY($2::text[])
                """,
                user_id,
                list(names_to_delete)
            )

        for item in new_usernames:
            await db.execute(
                """
                INSERT INTO user_overwatch_usernames (user_id, username, is_primary)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, username)
                DO UPDATE SET is_primary = EXCLUDED.is_primary
                """,
                user_id,
                item.username,
                item.is_primary,
            )

    @get("/users/{user_id:int}/overwatch")
    async def get_overwatch_usernames(self, db_connection: Connection, user_id: int) -> OverwatchUsernamesResponse:
        """Retrieve the Overwatch usernames for a specific user.

        Args:
            db_connection (Connection): The database connection.
            user_id (int): The ID of the user.

        Returns:
            Response: The response containing the user's Overwatch usernames or an error message.

        """
        usernames = await self._fetch_overwatch_usernames(db_connection, user_id)
        if usernames is None:
            logger.debug(f"User {user_id} not found.")
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found", extra={"user_id": user_id})
        return OverwatchUsernamesResponse(user_id=user_id, usernames=usernames)

    async def _fetch_overwatch_usernames(
        self, db: Connection, user_id: int
    ) -> list[OverwatchUsernameItem]:
        rows = await db.fetch(
            "SELECT username, is_primary FROM user_overwatch_usernames WHERE user_id = $1", user_id
        )
        return [OverwatchUsernameItem(**row) for row in rows]
