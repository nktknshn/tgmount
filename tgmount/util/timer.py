import time
from functools import wraps


class Timer:
    log_func = print

    class Interval:
        def __init__(self, name: str, log=False) -> None:
            self.name: str = name
            self.start: int = time.time_ns()
            self.end: int | None = None
            self._log = log

        def stop(self):
            if self.end is not None:
                return

            self.end = time.time_ns()

            if self._log:
                Timer.log_func(
                    f"Interval {self.name} stoped. Duration: {self.duration} ms"
                )

        @property
        def duration(self):
            return (self.end - self.start) / 1000 / 1000

    def __init__(self) -> None:
        self._intervals: list[Timer.Interval] = []
        self._interval_by_name: dict[str, Timer.Interval] = {}

    def start(self, interval_name: str, log=False):
        if log:
            self.log_func(f"Interval {interval_name} started!")

        if len(self._intervals) > 0:
            last = self._intervals[-1]
            last.stop()

        t = Timer.Interval(interval_name, log=log)
        self._intervals.append(t)
        self._interval_by_name[interval_name] = t

    def stop(self):
        last = self._intervals[-1]
        last.stop()

    def print(self):
        last = self._intervals[-1]

        if last.end is None:
            last.stop()

        for inter in self._intervals:
            print(f"{inter.name} lasted {inter.duration} ms")

    @property
    def intervals(self):
        return self._intervals[:]

    @property
    def durations(self):
        return {k: v.duration for k, v in self._interval_by_name.items()}

    @property
    def total(self):
        return sum(map(lambda inter: inter.duration, self.intervals))
