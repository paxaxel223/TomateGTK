from collections import namedtuple

from gi.repository import GLib
from wiring import inject, SingletonScope
from wiring.scanning import register

from . import State, SECONDS_IN_A_MINUTE
from .event import ObservableProperty, Timer as Dispatcher
from .fsm import fsm

ONE_SECOND = 1


class TimerPayload(namedtuple("TimerPayload", "time_left duration")):
    __slots__ = ()

    @property
    def remaining_ratio(self) -> float:
        try:
            return self.time_left / self.duration
        except ZeroDivisionError:
            return 0.0

    @property
    def elapsed_ratio(self) -> float:
        return round(1.0 - self.remaining_ratio, 1)

    @property
    def elapsed_percent(self):
        """
        Returns the percentage in 5% steps
        """
        percent = self.elapsed_ratio * 100
        return percent - percent % 5


# Based on Tomatoro create by Pierre Quillery.
# https://github.com/dandelionmood/Tomatoro
# Thanks Pierre!


@register.factory("tomate.timer", scope=SingletonScope)
class Timer:
    @inject(dispatcher="tomate.events.timer")
    def __init__(self, dispatcher: Dispatcher):
        self.duration = self.time_left = 0
        self._dispatcher = dispatcher

    @fsm(target=State.started, source=[State.finished, State.stopped])
    def start(self, seconds: int) -> bool:
        self.duration = self.time_left = seconds

        GLib.timeout_add_seconds(ONE_SECOND, self._update)

        return True

    @fsm(target=State.stopped, source=[State.started])
    def stop(self) -> bool:
        self._reset()

        return True

    def timer_is_up(self) -> bool:
        return self.time_left <= 0

    @fsm(target=State.finished, source=[State.started], condition=timer_is_up)
    def end(self) -> bool:
        return True

    def _update(self) -> bool:
        if self.state != State.started:
            return False

        if self.timer_is_up():
            return self.end()

        self.time_left -= 1

        self._trigger(State.changed)

        return True

    def _trigger(self, event) -> None:
        payload = TimerPayload(time_left=self.time_left, duration=self.duration)
        self._dispatcher.send(event, payload=payload)

    def _reset(self) -> None:
        self.duration = self.time_left = 0

    state = ObservableProperty(initial=State.stopped, callback=_trigger)


def format_time_left(seconds: int) -> str:
    minutes, seconds = divmod(seconds, SECONDS_IN_A_MINUTE)
    return "{0:0>2}:{1:0>2}".format(minutes, seconds)
