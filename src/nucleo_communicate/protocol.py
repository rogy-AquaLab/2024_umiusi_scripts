import asyncio
import logging

import serial_asyncio # type:ignore


_logger = logging.getLogger(__name__)


class RecvBuffer:
    def __init__(self) -> None:
        self._progress: int = 0
        self._flex1: int | None = None
        self._flex2: int | None = None
        self._current: int | None = None
        self._voltage: int | None = None

    def __str__(self) -> str:
        clsname = self.__class__.__name__
        flex1 = self._flex1
        flex2 = self._flex2
        current = self._current
        voltage = self._voltage
        return f"{clsname}({flex1=}, {flex2=}, {current=}, {voltage=})"

    @property
    def flex1(self) -> int:
        return self._flex1 if self._flex1 is not None else -1

    @property
    def flex2(self) -> int:
        return self._flex2 if self._flex2 is not None else -1

    @property
    def current(self) -> int:
        return self._current if self._current is not None else -1

    @property
    def voltage(self) -> int:
        return self._voltage if self._voltage is not None else -1

    def clear(self) -> None:
        self._progress = 0
        self._flex1 = None
        self._flex2 = None
        self._current = None
        self._voltage = None

    def append(self, value: int) -> None:
        match self._progress:
            case 0:
                self._flex1 = self._flex1 or 0
                self._flex1 |= (value & 0xFF) << 0
            case 1:
                self._flex1 = self._flex1 or 0
                self._flex1 |= (value & 0xFF) << 8
            case 2:
                self._flex2 = self._flex2 or 0
                self._flex2 |= (value & 0xFF) << 0
            case 3:
                self._flex2 = self._flex2 or 0
                self._flex2 |= (value & 0xFF) << 8
            case 4:
                self._current = self._current or 0
                self._current |= (value & 0xFF) << 0
            case 5:
                self._current = self._current or 0
                self._current |= (value & 0xFF) << 8
            case 6:
                self._voltage = self._voltage or 0
                self._voltage |= (value & 0xFF) << 0
            case 7:
                self._voltage = self._voltage or 0
                self._voltage |= (value & 0xFF) << 8
            case _:
                return
        self._progress += 1

    def extend(self, value: bytes) -> None:
        for v in value:
            self.append(v)

    def filled(self) -> bool:
        return self._progress > 7


class RecvProtocol(asyncio.Protocol):
    def __init__(self) -> None:
        super().__init__()
        self._transport: serial_asyncio.SerialTransport | None = None
        self._logger = _logger.getChild(self.__class__.__name__)
        self._buffer = RecvBuffer()

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

    def data_received(self, data: bytes) -> None:
        self._buffer.extend(data)
        if self._buffer.filled():
            self._logger.info(f"image filled: {self._buffer}")
        return super().data_received(data)


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
