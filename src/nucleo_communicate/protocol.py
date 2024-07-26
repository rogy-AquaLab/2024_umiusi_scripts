import asyncio
import logging

import serial_asyncio # type:ignore


_logger = logging.getLogger(__name__)


class LogProtocol(asyncio.Protocol):
    def __init__(self) -> None:
        super().__init__()
        self.transport: serial_asyncio.SerialTransport | None = None

    def connection_made(self, transport: serial_asyncio.SerialTransport) -> None:
        self.transport = transport
        _logger.info("Protocol.connection_made")
        return super().connection_made(transport)

    def connection_lost(self, exc: Exception | None) -> None:
        self.transport = None
        _logger.info(f"Protocol.connection_lost {exc=}")
        return super().connection_lost(exc)

    def data_received(self, data: bytes) -> None:
        _logger.info(f"Protocol.data_received {data=}")
        return super().data_received(data)

    def eof_received(self) -> bool | None:
        _logger.info(f"Protocol.eof_received")
        return super().eof_received()

    def pause_writing(self) -> None:
        _logger.info("Protocol.pause_writing")
        return super().pause_writing()

    def resume_writing(self) -> None:
        _logger.info("Protocol.resume_writing")
        return super().resume_writing()
