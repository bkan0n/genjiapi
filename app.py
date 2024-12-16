from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator

import aio_pika
from aio_pika.pool import Pool
from apitally.litestar import ApitallyPlugin
from litestar import Litestar, MediaType, Request, Response
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar_asyncpg import AsyncpgConfig, AsyncpgPlugin, PoolConfig

from controllers import (
    AutocompleteController,
    CompletionsController,
    LootboxController,
    MapsController,
    MasteryController,
    RankCardController,
    RanksController,
    RootRouter,
)
from controllers.newsfeed.newsfeed import NewsfeedController

if TYPE_CHECKING:
    from aio_pika.abc import AbstractRobustConnection

log = logging.getLogger(__name__)


def plain_text_exception_handler(_: Request, exc: Exception) -> Response:
    """Handle exceptions subclassed from HTTPException."""
    status_code = getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", "")

    return Response(
        media_type=MediaType.TEXT,
        content=detail,
        status_code=status_code,
    )


logging_config = LoggingConfig(
    root={"level": "INFO", "handlers": ["queue_listener"]},
    formatters={"standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
    log_exceptions="always",
)


psql_user = os.getenv("PSQL_USER")
psql_pass = os.getenv("PSQL_PASS")
psql_host = os.getenv("PSQL_HOST")
psql_port = os.getenv("PSQL_PORT")
psql_db = os.getenv("PSQL_DB")

dsn = f"postgresql://{psql_user}:{psql_pass}@{psql_host}:{psql_port}/{psql_db}"

asyncpg = AsyncpgPlugin(config=AsyncpgConfig(pool_config=PoolConfig(dsn=dsn)))

apitally_plugin = ApitallyPlugin(
    client_id="765ee232-a48d-449a-8093-77b670e91f37",
    env="prod",  # or "dev"
)


rabbitmq_user = os.getenv("RABBITMQ_DEFAULT_USER")
rabbitmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS")


@asynccontextmanager
async def rabbitmq_connection(app: Litestar) -> AsyncGenerator[None, None]:
    _conn = getattr(app.state, "rabbitmq_connection", None)
    if _conn is None:

        async def get_connection() -> AbstractRobustConnection:
            return await aio_pika.connect_robust(f"amqp://{rabbitmq_user}:{rabbitmq_pass}@genji-rabbit/")

        connection_pool: Pool = Pool(get_connection, max_size=2)

        async def get_channel() -> aio_pika.Channel:
            async with connection_pool.acquire() as connection:
                return await connection.channel()

        channel_pool: Pool = Pool(get_channel, max_size=10)

        app.state.mq_channel_pool = channel_pool
    yield


app = Litestar(
    plugins=[asyncpg, apitally_plugin],
    route_handlers=[
        RootRouter(
            path="/v1",
            route_handlers=[
                MapsController,
                CompletionsController,
                LootboxController,
                RanksController,
                AutocompleteController,
                NewsfeedController,
                MasteryController,
                RankCardController,
            ],
        )
    ],
    openapi_config=OpenAPIConfig(
        title="GenjiAPI",
        description="GenjiAPI",
        version="0.1.0",
        path="/docs",
    ),
    exception_handlers={HTTPException: plain_text_exception_handler},
    logging_config=logging_config,
    lifespan=[rabbitmq_connection],
)
