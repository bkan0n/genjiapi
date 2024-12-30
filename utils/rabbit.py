import typing

import aio_pika
import msgspec
from litestar.datastructures import State


class RabbitMessageBody(msgspec.Struct):
    type: str
    data: typing.Any


async def publish(
    state: State,
    message_type: str,
    data: msgspec.Struct | list[msgspec.Struct],
    routing_key: str = "genjiapi",
    extra_headers: dict | None = None,
) -> None:
    """Publish message to RabbitMQ."""
    async with state.mq_channel_pool.acquire() as channel:  # type: aio_pika.Channel
        message_body = msgspec.json.encode(data)

        if extra_headers is None:
            extra_headers = {}

        message = aio_pika.Message(
            message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"x-type": message_type, **extra_headers},
        )

        await channel.default_exchange.publish(
            message,
            routing_key=routing_key,
        )
