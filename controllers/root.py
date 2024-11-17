import os

from litestar import Controller, Router
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_403_FORBIDDEN


async def api_key_guard(connection: ASGIConnection, _) -> None:
    api_key = connection.headers.get("X-API-KEY")
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid or missing API key")

class RootRouter(Router):
    guards = [api_key_guard]