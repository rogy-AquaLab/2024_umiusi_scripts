import asyncio
import logging
from collections import deque
from typing import Any

import aiochannel
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from typing_extensions import Generator, NoReturn

_logger = logging.getLogger(__name__)


class SensorValueAnimationHandle:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        rx: aiochannel.Channel[int],
        ax: Axes,
        value_scale: float = 1 / (1 << 16)
    ) -> None:
        self._loop = loop
        self._rx = rx
        self._ax = ax
        self._value_scale = value_scale
        self._index = 0
        self._xdata = deque[float]()
        self._ydata = deque[float]()
        self._line, *_ = self._ax.plot(self._xdata, self._ydata)
        self._line.set_marker("o")
        self._line.set_linestyle("none")
        self._logger = _logger.getChild(self.__class__.__name__)

    def init(self) -> tuple[Axes]:
        self._ax.set_xlim(0.0, 50.0)
        self._ax.set_ylim(0.0, 1.0)
        return (self._ax,)

    def frames(self) -> Generator[float | None, None, NoReturn]:
        while True:
            try:
                frame_future = asyncio.run_coroutine_threadsafe(self._rx.get(), self._loop)
                yield frame_future.result(0.01)
            except asyncio.TimeoutError:
                yield None
            finally:
                self._logger.debug("yielded frame")

    def update(self, frame: float | None) -> tuple[Axes]:
        if frame is None:
            return (self._ax,)
        self._xdata.append(self._index)
        self._ydata.append(frame * self._value_scale)
        if self._index > 100:
            xleft = self._xdata.popleft()
            self._ydata.popleft()
            self._ax.set_xlim(xleft, self._index)
        self._line.set_data(self._xdata, self._ydata)
        self._index += 1
        return (self._ax,)

    def create_animation(self, fig: Figure, *args: Any, **kwargs: Any) -> FuncAnimation:
        kwargs["frames"] = self.frames
        kwargs["init_func"] = self.init
        return FuncAnimation(fig, self.update, *args, **kwargs)
