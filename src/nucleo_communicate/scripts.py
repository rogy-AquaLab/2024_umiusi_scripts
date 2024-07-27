import asyncio
import contextlib
import logging
import sys
from concurrent import futures
from functools import partial
from threading import Event

import aiochannel
import matplotlib.pyplot as plt
import serial_asyncio # type: ignore

from .protocol import RecvBuffer, RecvChanProtocol, RecvProtocol
from .plot_anime import SensorValueAnimationHandle


_logger = logging.getLogger(__name__)


async def read_forever(loop: asyncio.AbstractEventLoop):
    _transport, protocol = await serial_asyncio.create_serial_connection(loop, RecvProtocol, "/dev/ttyACM0")
    assert isinstance(protocol, RecvProtocol)
    await protocol.wait_connected()
    while True:
        _logger.info("tick")
        protocol.request_data()
        await asyncio.sleep(0.5)


def run_read_forever():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(read_forever(loop))


async def flex1_anime_backend(loop: asyncio.AbstractEventLoop, frame_tx: aiochannel.Channel[float], terminate: Event) -> None:
    buffer_ch: aiochannel.Channel[RecvBuffer] = aiochannel.Channel(1)
    protocol_factory = partial(RecvChanProtocol, loop, buffer_ch)
    _transport, protocol = await serial_asyncio.create_serial_connection(loop, protocol_factory, "/dev/ttyACM0")

    async def bridge() -> None:
        async for buf in buffer_ch:
            assert isinstance(buf, RecvBuffer) and buf.flex1 is not None
            value = buf.flex1 / 0xFFFF
            put_coro = frame_tx.put(value)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(put_coro, 0.1)

    async def request_loop() -> None:
        while not terminate.is_set():
            protocol.request_data()
            await asyncio.sleep(0.05)

    assert isinstance(protocol, RecvChanProtocol)
    await protocol.wait_connected()
    bridge_task = asyncio.create_task(bridge())
    reqloop_task = asyncio.create_task(request_loop())
    await asyncio.wait([bridge_task, reqloop_task], return_when=asyncio.FIRST_COMPLETED)


def flex1_animation() -> None:
    logging.getLogger("asyncio").setLevel(logging.DEBUG)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    loop = asyncio.get_event_loop()
    fig, ax = plt.subplots()
    ax.set_title("flex1 value")
    ch: aiochannel.Channel[float] = aiochannel.Channel()
    handle = SensorValueAnimationHandle(loop, ch, ax)
    terminate = Event()

    def run_backend() -> None:
        coro = flex1_anime_backend(loop, ch, terminate)
        loop.run_until_complete(coro)

    with futures.ThreadPoolExecutor() as pool:
        fut = pool.submit(run_backend)
        _anime = handle.create_animation(fig, save_count=10, interval=20)
        plt.show()
        terminate.set()
        fut.result(1)
