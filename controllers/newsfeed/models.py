import datetime

import msgspec


class NewsfeedRecordResponse(msgspec.Struct, omit_defaults=True):
    record: float | None = None
    video: str | None = None
    rank_num: int | None = None


class NewsfeedUserResponse(msgspec.Struct, omit_defaults=True):
    user_id: int | None = None
    nickname: str | None = None
    roles: list[str] | None = None


class NewsfeedMapResponse(msgspec.Struct, omit_defaults=True):
    map_name: str | None = None
    map_type: list[str] | None = None
    map_code: str | None = None
    new_map_code: str | None = None
    desc: str | None = None
    official: bool | None = None
    archived: bool | None = None
    guide: list[str] | None = None
    mechanics: list[str] | None = None
    restrictions: list[str] | None = None
    checkpoints: int | None = None
    creators: list[str] | None = None
    difficulty: str | None = None
    quality: float | None = None
    creator_ids: list[int] | None = None
    gold: float | None = None
    silver: float | None = None
    bronze: float | None = None


class NewsfeedMessageResponse(msgspec.Struct, omit_defaults=True):
    content: str


class NewsfeedDataResponse(msgspec.Struct, omit_defaults=True):
    map: NewsfeedMapResponse | None = None
    user: NewsfeedUserResponse | None = None
    record: NewsfeedRecordResponse | None = None
    message: NewsfeedMessageResponse | None = None
    bulk: list[NewsfeedMapResponse] | None = None


class NewsfeedResponse(msgspec.Struct):
    type: str
    timestamp: datetime.datetime
    data: NewsfeedDataResponse
    total_results: int


class GlobalNameResponse(msgspec.Struct):
    name: str
