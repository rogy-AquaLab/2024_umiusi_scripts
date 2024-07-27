import asyncio
import contextlib
import logging
from dataclasses import dataclass

import aiochannel
import serial_asyncio # type:ignore


_logger = logging.getLogger(__name__)


@dataclass(frozen=False)
class RecvBuffer:
    flex1: int | None = None
    flex2: int | None = None
    current: int | None = None
    voltage: int | None = None

    def clear(self) -> None:
        self.flex1 = None
        self.flex2 = None
        self.current = None
        self.voltage = None


class RecvProtocol(asyncio.Protocol):
    def __init__(self) -> None:
        super().__init__()
        self._transport: serial_asyncio.SerialTransport | None = None
        self._logger = _logger.getChild(self.__class__.__name__)
        self._buffer = RecvBuffer()
        self._buffer_progress = 0

    def connection_made(self, transport: serial_asyncio.SerialTransport) -> None:
        self._transport = transport
        self._logger.debug("connection made")
        return super().connection_made(transport)

    def connection_lost(self, exc: Exception | None) -> None:
        self._transport = None
        self._logger.debug(f"connection lost: {exc=}")
        return super().connection_lost(exc)

    def request_data(self) -> None:
        assert self._transport is not None
        self._transport.write(bytes([0x01]))
        self._buffer.clear()
        self._buffer_progress = 0

    def _append_data(self, value: int) -> None:
        match self._buffer_progress:
            case 0:
                self._buffer.flex1 = self._buffer.flex1 or 0
                self._buffer.flex1 |= (value & 0xFF) << 0
            case 1:
                assert self._buffer.flex1 is not None
                self._buffer.flex1 |= (value & 0xFF) << 8
            case 2:
                self._buffer.flex2 = self._buffer.flex2 or 0
                self._buffer.flex2 |= (value & 0xFF) << 0
            case 3:
                assert self._buffer.flex2 is not None
                self._buffer.flex2 |= (value & 0xFF) << 8
            case 4:
                self._buffer.current = self._buffer.current or 0
                self._buffer.current |= (value & 0xFF) << 0
            case 5:
                assert self._buffer.current is not None
                self._buffer.current |= (value & 0xFF) << 8
            case 6:
                self._buffer.voltage = self._buffer.voltage or 0
                self._buffer.voltage |= (value & 0xFF) << 0
            case 7:
                assert self._buffer.voltage is not None
                self._buffer.voltage |= (value & 0xFF) << 8
            case _:
                return
        self._buffer_progress += 1

    def _filled_buffer(self):
        return self._buffer_progress > 7

    def data_received(self, data: bytes) -> None:
        for v in data:
            self._append_data(v)
        if self._filled_buffer():
            self._logger.info(f"image filled: {self._buffer}")
        return super().data_received(data)

    def get_buffer(self) -> RecvBuffer:
        return RecvBuffer(self._buffer.flex1, self._buffer.flex2, self._buffer.current, self._buffer.voltage)


class RecvChanProtocol(RecvProtocol):
    def __init__(self, loop: asyncio.AbstractEventLoop, tx: aiochannel.Channel[RecvBuffer]) -> None:
        super().__init__()
        self._loop = loop
        self._tx = tx

    def _send_buffer(self, buffer: RecvBuffer) -> None:
        with contextlib.suppress(asyncio.TimeoutError):
            put_coro = asyncio.wait_for(self._tx.put(buffer), 0.1)
            asyncio.run_coroutine_threadsafe(put_coro, self._loop)

    def data_received(self, data: bytes) -> None:
        ret = super().data_received(data)
        if self._filled_buffer():
            buf = self.get_buffer()
            self._send_buffer(buf)
        return ret


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
