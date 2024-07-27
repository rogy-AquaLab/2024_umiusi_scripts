import asyncio
import logging
import sys

import serial_asyncio # type: ignore

from .protocol import RecvProtocol


_logger = logging.getLogger(__name__)


async def read_forever(loop: asyncio.AbstractEventLoop):
    _transport, protocol = await serial_asyncio.create_serial_connection(loop, RecvProtocol, "/dev/ttyACM0")
    assert isinstance(protocol, RecvProtocol)
    while True:
        await asyncio.sleep(0.5)
        _logger.info("tick")
        protocol.request_data()


def run_read_forever():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(read_forever(loop))
