import typing

import aio_pika
import msgspec
from litestar.datastructures import State


class RabbitMessageBody(msgspec.Struct):
    type: str
    data: typing.Any


async def publish(state: State, message_type: str, data: msgspec.Struct, routing_key: str = "genjiapi") -> None:
    """Publish message to RabbitMQ."""
    async with state.mq_channel_pool.acquire() as channel:  # type: aio_pika.Channel
        message_body = msgspec.json.encode(data)

        message = aio_pika.Message(
            message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"x-type": message_type},
        )

        await channel.default_exchange.publish(
            message,
            routing_key=routing_key,
        )
