import os
import typing

from litestar import Controller, Router
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException
from litestar.handlers import BaseRouteHandler
from litestar.status_codes import HTTP_403_FORBIDDEN


async def api_key_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Check if API key is valid."""
    api_key = connection.headers.get("X-API-KEY")
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid or missing API key")


class BaseControllerV2(Controller):
    guards = [api_key_guard]


class RootRouterV2(Router):
    guards: typing.ClassVar = [api_key_guard]
