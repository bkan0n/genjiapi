from __future__ import annotations

from asyncpg import Connection  # noqa: TCH002
from litestar import get

from ..root import BaseController


class SettingsController(BaseController):
    path = "/settings"
    tags = ["Settings"]

    @get("/settings/{user_id:int}")
    async def get_settings(self, user_id: int):
        ...

    @get("/test")
    async def get_test(self) -> str:
        1 / 0
        return "test"
