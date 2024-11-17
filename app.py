from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from litestar import Litestar, Response, Request, MediaType
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar_asyncpg import AsyncpgConfig, AsyncpgPlugin, PoolConfig

from controllers.completions import CompletionsController
from controllers.lootbox import LootboxController
from controllers.maps import MapsController
from controllers.ranks import RanksController
from controllers.root import RootRouter

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


def plain_text_exception_handler(_: Request, exc: Exception) -> Response:
    """Default handler for exceptions subclassed from HTTPException."""
    status_code = getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", "")

    return Response(
        media_type=MediaType.TEXT,
        content=detail,
        status_code=status_code,
    )


logging_config = LoggingConfig(
    root={"level": "INFO", "handlers": ["queue_listener"]},
    formatters={
        "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    },
    log_exceptions="always",
)


psql_user = os.getenv("PSQL_USER")
psql_pass = os.getenv("PSQL_PASS")
psql_host = os.getenv("PSQL_HOST")
psql_port = os.getenv("PSQL_PORT")
psql_db = os.getenv("PSQL_DB")

dsn = f"postgresql://{psql_user}:{psql_pass}@{psql_host}:{psql_port}/{psql_db}"

asyncpg = AsyncpgPlugin(config=AsyncpgConfig(pool_config=PoolConfig(dsn=dsn)))
app = Litestar(
    plugins=[asyncpg],
    route_handlers=[RootRouter(path="/v1", route_handlers=[
        MapsController, CompletionsController, LootboxController, RanksController
    ])],
    openapi_config=OpenAPIConfig(
        title="GenjiAPI",
        description="GenjiAPI",
        version="0.1.0",
        path="/docs",
    ),
    exception_handlers={HTTPException: plain_text_exception_handler},
    logging_config=logging_config,
)

