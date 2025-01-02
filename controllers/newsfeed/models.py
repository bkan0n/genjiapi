import datetime

import msgspec


class NewsfeedRecordResponse(msgspec.Struct, omit_defaults=True):
    record: float = None
    video: str = None


class NewsfeedUserResponse(msgspec.Struct, omit_defaults=True):
    user_id: int = None
    nickname: str = None
    roles: list[str] = None


class NewsfeedMapResponse(msgspec.Struct, omit_defaults=True):
    map_name: str = None
    map_type: list[str] = None
    map_code: str = None
    new_map_code: str = None
    desc: str = None
    official: bool = None
    archived: bool = None
    guide: list[str] = None
    mechanics: list[str] = None
    restrictions: list[str] = None
    checkpoints: int = None
    creators: list[str] = None
    difficulty: str = None
    quality: float = None
    creator_ids: list[int] = None
    gold: float = None
    silver: float = None
    bronze: float = None


class NewsfeedMessageResponse(msgspec.Struct, omit_defaults=True):
    content: str


class NewsfeedDataResponse(msgspec.Struct, omit_defaults=True):
    map: NewsfeedMapResponse = None
    user: NewsfeedUserResponse = None
    record: NewsfeedRecordResponse = None
    message: NewsfeedMessageResponse = None
    bulk: list[NewsfeedMapResponse] = None


class NewsfeedResponse(msgspec.Struct):
    type: str
    timestamp: datetime.datetime
    data: NewsfeedDataResponse
    total_results: int


class GlobalNameResponse(msgspec.Struct):
    name: str
