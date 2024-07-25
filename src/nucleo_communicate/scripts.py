import asyncio

import serial_asyncio # type: ignore

from .protocol import Protocol


async def read_forever(loop: asyncio.AbstractEventLoop):
    transport, _protocol = await serial_asyncio.create_serial_connection(loop, Protocol, "/dev/ttyACM0")
    while True:
        await asyncio.sleep(0.5)
        transport.write(bytes([0x01]))


def run_read_forever():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(read_forever(loop))
