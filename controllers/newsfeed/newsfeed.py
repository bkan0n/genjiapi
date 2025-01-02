import json
from typing import Annotated, Literal

from asyncpg import Connection, Record
from litestar import get
from litestar.exceptions import HTTPException
from litestar.params import Parameter

from utils.utilities import convert_num_to_difficulty

from ..root import BaseController
from .models import (
    GlobalNameResponse,
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

        map_data = None
        user_data = None
        record_data = None
        message_data = None
        bulk_data = None

        if isinstance(data_dict, dict):
            user_data = NewsfeedUserResponse(**data_dict.get("user", {})) if "user" in data_dict else None
            map_data = NewsfeedMapResponse(**data_dict.get("map", {})) if "map" in data_dict else None
            record_data = NewsfeedRecordResponse(**data_dict.get("record", {})) if "record" in data_dict else None
            message_data = NewsfeedMessageResponse(**data_dict.get("message", {})) if "message" in data_dict else None
        elif isinstance(data_dict, list):
            print(data_dict)
            bulk_data = [NewsfeedMapResponse(**(m["map"])) for m in data_dict]

        data = NewsfeedDataResponse(
            map=map_data, user=user_data, record=record_data, message=message_data, bulk=bulk_data
        )
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

    @get(path="/discord/{user_id:int}")
    async def get_global_name(
        self,
        db_connection: Connection,
        user_id: int,
    ) -> GlobalNameResponse:
        """Get Global Name."""
        query = "SELECT global_name as name FROM user_global_names WHERE user_id = $1;"
        row = await db_connection.fetchrow(query, user_id)
        if not row:
            raise HTTPException(detail="User ID not found.", status_code=404)
        return GlobalNameResponse(**row)
