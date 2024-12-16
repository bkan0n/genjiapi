import json
from typing import Annotated, Literal

from aio_pika import DeliveryMode, Message
from asyncpg import Connection, Record
from litestar import get
from litestar.datastructures import State
from litestar.params import Parameter

from utils.utilities import convert_num_to_difficulty

from ..root import BaseController
from .models import (
    NewsfeedDataResponse,
    NewsfeedMapResponse,
    NewsfeedMessageResponse,
    NewsfeedRecordResponse,
    NewsfeedResponse,
    NewsfeedUserResponse,
)


class NewsfeedController(BaseController):
    path = "/newsfeed"
    tags = ["newsfeed"]

    @staticmethod
    def _parse_newsfeed_row(row: Record) -> NewsfeedResponse:
        type_ = row["type"]
        timestamp = row["timestamp"]
        data_json = row["data"]
        total_results = row["total_results"]

        data_dict = json.loads(data_json)

        user_data = NewsfeedUserResponse(**data_dict.get("user", {})) if "user" in data_dict else None
        map_data = NewsfeedMapResponse(**data_dict.get("map", {})) if "map" in data_dict else None
        record_data = NewsfeedRecordResponse(**data_dict.get("record", {})) if "record" in data_dict else None
        message_data = NewsfeedMessageResponse(**data_dict.get("message", {})) if "message" in data_dict else None

        data = NewsfeedDataResponse(map=map_data, user=user_data, record=record_data, message=message_data)
        return NewsfeedResponse(type=type_, timestamp=timestamp, data=data, total_results=total_results)

    @get(path="/")
    async def get_newsfeed(
        self,
        db_connection: Connection,
        page_size: Literal[10, 20, 25, 50] = 10,
        page_number: Annotated[int, Parameter(ge=1)] = 1,
        type_: Annotated[
            Literal["map_edit", "guide", "new_map", "role", "record", "announcement"] | None, Parameter(query="type")
        ] = None,
    ) -> list[NewsfeedResponse]:
        """Get newsfeed."""
        query = """
            SELECT
                type, timestamp, data::jsonb,
                count(*) OVER() as total_results
            FROM newsfeed
            WHERE $3::text IS NULL OR type = $3
            GROUP BY type, timestamp, data::jsonb
            ORDER BY timestamp DESC
            LIMIT $1
            OFFSET $2;
            """
        offset = (page_number - 1) * page_size
        rows = await db_connection.fetch(query, page_size, offset, type_)
        responses = []
        for row in rows:
            if row.get("difficulty") and isinstance(row["difficulty"], float):
                row["difficulty"] = convert_num_to_difficulty(row["difficulty"])
            responses.append(self._parse_newsfeed_row(row))
        return responses

    @get(path="/aaa")
    async def aaa(self, state: State) -> str:
        """Test."""
        async with state.mq_channel_pool.acquire() as channel:  # type: aio_pika.Channel
            message_body = json.dumps({"new_map": {"map_code": "123123"}}).encode("utf-8")

            message = Message(
                message_body,
                delivery_mode=DeliveryMode.PERSISTENT,
            )

            await channel.default_exchange.publish(
                message,
                routing_key="genjiapi",
            )

        return "Yes!"
