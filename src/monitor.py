from time import sleep
import logging
from typing import Any
from typing import Callable, Awaitable

from faststream import FastStream, Logger, Depends, BaseMiddleware
from faststream.broker.message import StreamMessage
from faststream.redis import PubSub, RedisBroker
from redis.sentinel import Sentinel

sentinels = [('sentinel-0', 26379), ('sentinel-1', 26379), ('sentinel-2', 26379)]
sentinel = Sentinel(
    sentinels=sentinels,
    socket_timeout=0.1
)

class QuitMiddleware(BaseMiddleware):
    async def publish_scope(
        self,
        call_next: Callable[..., Awaitable[Any]],
        msg: Any,
        **options: Any,
    ) -> Any:
        try:
            return await call_next(msg, **options)
        except Exception as e:
            logger = logging.getLogger("faststream")
            logger.warning("oh no")
            logger.fatal(e, exc_info=True)
            await master_broker.close()
            # await sentinel_broker.close()
            app.exit()

master_broker = RedisBroker(middlewares=[QuitMiddleware])

async def master_setup():
    logger = logging.getLogger("faststream")
    (master_url, port) = sentinel.discover_master("dc")
    logger.info("running master setup")
    logger.info(f"Current master={master_url, port}")
    url = f"redis://{master_url}"
    await master_broker.connect(url=url, port=port)

sentinel_broker = RedisBroker(middlewares=[QuitMiddleware])
app = FastStream(sentinel_broker)

@app.on_startup
async def sentinel_setup():
    await master_setup()

    # the logger in context doesn't seem to be properly configured
    # and is not at info level
    logger = logging.getLogger("faststream")
    logger.info(sentinel)

    # TODO try all 3 then give up
    (url, port) = sentinels[0]
    url = f"redis://{url}"
    await sentinel_broker.connect(url=url, port=port)

@sentinel_broker.subscriber(channel=PubSub("*", pattern=True))
@master_broker.publisher(channel="monitor-events")
async def monitor_events(msg: Any, logger: Logger):
    logger.info(msg)
    return msg

@sentinel_broker.subscriber(channel="+switch-master")
@master_broker.publisher(channel="switch-master")
async def switch_master(msg: Any, logger: Logger):
    logger.error("Master changed")
    logger.error("I will notify the others, before I die...")

@app.after_startup
async def current_master():
    while True:
        master = sentinel.discover_master("dc")
        await master_broker.publish(message=master, channel="current-master")
        sleep(5)
