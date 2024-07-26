import asyncio
import logging
import sys

import serial_asyncio # type: ignore

from .protocol import LogProtocol


_logger = logging.getLogger(__name__)


async def read_forever(loop: asyncio.AbstractEventLoop):
    transport, _protocol = await serial_asyncio.create_serial_connection(loop, LogProtocol, "/dev/ttyACM0")
    while True:
        await asyncio.sleep(0.5)
        _logger.info("tick")
        transport.write(bytes([0x01]))


def run_read_forever():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(read_forever(loop))
