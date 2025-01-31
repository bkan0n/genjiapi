from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

import aio_pika
import sentry_sdk
from aio_pika.pool import Pool
from litestar import Litestar, MediaType, Request, Response, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.middleware import DefineMiddleware
from litestar.openapi import OpenAPIConfig
from litestar.plugins.problem_details import ProblemDetailsConfig, ProblemDetailsPlugin
from litestar.static_files import create_static_files_router
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.template import TemplateConfig
from litestar_asyncpg import AsyncpgConfig, AsyncpgPlugin, PoolConfig
from sentry_sdk.integrations.litestar import LitestarIntegration

from controllers import (
    AutocompleteController,
    CompletionsController,
    LootboxController,
    MapsController,
    RankCardController,
    RanksController,
    RootRouter,
)
from controllers.newsfeed.newsfeed import NewsfeedController
from controllers.rank_card.mastery import MasteryController
from middleware.umami import UmamiMiddleware

if TYPE_CHECKING:
    from aio_pika.abc import AbstractRobustConnection

log = logging.getLogger(__name__)

sentry_dsn = os.getenv("SENTRY_DSN")
sentry_sdk.init(
    dsn=sentry_dsn,
    enable_tracing=True,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    integrations=[
        LitestarIntegration(),
    ],
)


def plain_text_exception_handler(_: Request, exc: Exception) -> Response[str]:
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

rabbitmq_user = os.getenv("RABBITMQ_DEFAULT_USER")
rabbitmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS")


@asynccontextmanager
async def rabbitmq_connection(app: Litestar) -> AsyncGenerator[None, None]:
    """Connect to RabbitMQ."""
    _conn = getattr(app.state, "rabbitmq_connection", None)
    if _conn is None:

        async def get_connection() -> AbstractRobustConnection:
            return await aio_pika.connect_robust(f"amqp://{rabbitmq_user}:{rabbitmq_pass}@genji-rabbit/")

        connection_pool: Pool[AbstractRobustConnection] = Pool(get_connection, max_size=2)

        async def get_channel() -> aio_pika.Channel:
            async with connection_pool.acquire() as connection:
                return await connection.channel()  # type: ignore

        channel_pool: Pool[AbstractRobustConnection] = Pool(get_channel, max_size=10)

        app.state.mq_channel_pool = channel_pool
    yield


UMAMI_API_ENDPOINT = os.getenv("UMAMI_API_ENDPOINT")
UMAMI_SITE_ID = os.getenv("UMAMI_SITE_ID")

problem_details_plugin = ProblemDetailsPlugin(ProblemDetailsConfig(enable_for_all_http_exceptions=True))

@get()
def root_handler() -> None:
    """Root path."""
    return None

app = Litestar(
    plugins=[
        asyncpg,
        problem_details_plugin,
    ],
    route_handlers=[
        root_handler,
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
        ),
        create_static_files_router(
            path="/assets",
            directories=["assets"],
            send_as_attachment=True,
        ),
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
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
    middleware=[
        DefineMiddleware(UmamiMiddleware, api_endpoint=UMAMI_API_ENDPOINT, website_id=UMAMI_SITE_ID),
    ],
)
# Ignore annoying apitally and analytics INFO logs
for logger_name in logging.Logger.manager.loggerDict:
    if "api" in logger_name or "httpx" in logger_name:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


