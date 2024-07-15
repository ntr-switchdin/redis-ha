from time import sleep
import logging
from typing import Any
from typing import Callable, Awaitable

from faststream import FastStream, Logger, Depends, BaseMiddleware
from faststream.broker.message import StreamMessage
from faststream.redis import PubSub, RedisBroker
from redis.sentinel import Sentinel

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
            logger.fatal(e, exc_info=True)
            app.exit()

broker = RedisBroker(middlewares=[QuitMiddleware])
app = FastStream(broker)

sentinel = Sentinel(
    sentinels=[('sentinel-0', 26379), ('sentinel-1', 26379), ('sentinel-2', 26379)],
    socket_timeout=0.1
)

@app.on_startup
async def setup():
    log = logging.getLogger("faststream")
    log.info(sentinel)

    (master_url, port) = sentinel.discover_master("dc")
    log.info(f"Consumer has its master={master_url, port}")
    url = f"redis://{master_url}"
    await broker.connect(url=url, port=port)

@broker.subscriber(channel="monitor-events")
async def monitor_events(msg: str, logger: Logger):
    logger.info(f"Monitor event={msg}")

@broker.subscriber(channel="switch-master")
async def switch_master(msg: str, logger: Logger):
    logger.error(f"Master has changed={msg}")
    logger.error("Shutting down...")
    app.exit()

@broker.subscriber(channel="current-master")
@broker.publisher(channel="health-checks")
async def current_master(msg: Any, logger: Logger):
    return msg

@broker.subscriber(channel="health-checks")
async def health_checks(msg: Any, logger: Logger):
    logger.info(msg)
