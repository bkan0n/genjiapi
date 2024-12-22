from __future__ import annotations

from asyncpg import Connection  # noqa: TCH002
from litestar import get

from utils.utilities import MAP_NAME_T  # noqa: TCH001

from ..root import BaseController
from .models import MapMasteryData, fetch_map_mastery


class MasteryController(BaseController):
    path = "/mastery"
    tags = ["Mastery"]

    @get(path="/{user_id:int}")
    async def fetch_user_mastery(
        self,
        db_connection: Connection,
        user_id: int,
        map_name: MAP_NAME_T | None = None,
    ) -> list[MapMasteryData]:
        """Fetch Map Mastery for a particular user."""
        return await fetch_map_mastery(db_connection, user_id, map_name)
