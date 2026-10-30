"""Timer module for measuring and logging task execution durations."""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Self


def format_time_ns(ns: int) -> str:
    """Format a duration in nanoseconds into human-readable units.

    Units:
        - < 1 μs: #ns (rounded to 1 decimal place)
        - < 1 ms: #μs (rounded to 1 decimal place)
        - < 1 s:  #ms (rounded to 1 decimal place)
        - < 1 m:  #s  (rounded to 1 decimal place)
        - < 1 h:  #m #s (integer minutes and seconds)
        - >= 1 h: #h #m #s (integer hours, minutes, and seconds)

    Args:
        ns: Duration in nanoseconds.

    Returns:
        Formatted time string.
    """
    duration = max(0, ns)

    if duration < 1e3:
        return f"{duration:.1f}ns"

    # < 1 millisecond (1,000,000 ns)
    if duration < 1e6:
        return f"{duration / 1e3:.1f}\u03BCs"

    # < 1 second (1,000,000,000 ns)
    if duration < 1e9:
        return f"{duration / 1e6:.1f}ms"

    # < 1 minute (60,000,000,000 ns)
    if duration < 60e9:
        return f"{duration / 1e9:.1f}s"

    # >= 1 minute: integer minutes and seconds
    total_seconds = round(duration / 1e9)
    if total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"

    # >= 1 hour: integer hours, minutes, and seconds
    hours = total_seconds // 3600
    rem = total_seconds % 3600
    minutes = rem // 60
    seconds = rem % 60
    return f"{hours}h {minutes}m {seconds}s"


class Timer:
    """A context manager for measuring and reporting execution time of code blocks.

    Logs a starting message on entry and either a completion or failure message
    upon exit.
    """

    def __init__(
        self,
        task_name: str | None = None,
        logger: logging.Logger | None = None,
        log_level: int | str | None = None,
    ) -> None:
        """Initialize the Timer context manager.

        Args:
            task_name: Optional descriptive name for the task.
            logger: Optional logger to record messages to. If None, prints to stdout.
            log_level: Optional logging level (e.g. logging.INFO, 'DEBUG'). Defaults to INFO.
        """
        self.task_name = task_name
        self.logger = logger
        self.log_level = log_level
        self.start_ns: int = 0
        self.end_ns: int = 0
        self.elapsed_ns: int = 0

    def __enter__(self) -> Self:
        current_time = time.strftime("%H:%M:%S")
        self.start_ns = time.perf_counter_ns()

        if self.task_name is not None:
            msg = f"Starting task: {self.task_name} at {current_time}"
        else:
            msg = f"Starting task at {current_time}"

        self._write(msg)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.end_ns = time.perf_counter_ns()
        self.elapsed_ns = self.end_ns - self.start_ns
        elapsed_str = format_time_ns(self.elapsed_ns)

        if exc_type is None:
            if self.task_name is not None:
                msg = f"Task completed in {elapsed_str}: {self.task_name}"
            else:
                msg = f"Task completed in {elapsed_str}"
        else:
            if self.task_name is not None:
                msg = f"Task failed after {elapsed_str}: {self.task_name}"
            else:
                msg = f"Task failed after {elapsed_str}"

        self._write(msg)

    def _write(self, message: str) -> None:
        if self.logger is not None:
            level = self._resolve_level(self.log_level)
            self.logger.log(level, message)
        else:
            print(message)

    @staticmethod
    def _resolve_level(level: int | str | None) -> int:
        if level is None:
            return logging.INFO
        if isinstance(level, str):
            level_map = logging.getLevelNamesMapping()
            return level_map.get(level.upper(), logging.INFO)
        return level


# Alias for lower-case context manager usage
timer = Timer
