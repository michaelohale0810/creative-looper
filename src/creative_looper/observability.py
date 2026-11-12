"""Telling people what a run is doing: log file, progress lines, heartbeat and token usage."""

import logging
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from crewai import LLM
from crewai.tasks.task_output import TaskOutput
from crewai.types.usage_metrics import UsageMetrics

logger = logging.getLogger("creative_looper")

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_run_handlers: list[logging.Handler] = []  # handlers of the run currently being logged
HEARTBEAT_SECONDS = 15


def format_elapsed(seconds: float) -> str:
    """Compact duration such as '45s' or '2m10s'."""
    seconds = int(seconds)
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m{secs:02d}s" if minutes else f"{secs}s"


def setup_run_logging(run_dir: Path, verbose: bool = False) -> Path:
    """Send all logging (ours and the libraries') to run_dir/run.log.

    Library warnings such as retries and rate limits land here instead of being
    hidden or cluttering the console. With `verbose` they also go to stderr.
    Calling it again (the next run of a loop) first detaches the previous run's
    handlers, so each run's log holds only that run.
    """
    for handler in _run_handlers:
        logging.getLogger().removeHandler(handler)
        handler.close()
    _run_handlers.clear()

    log_path = run_dir / "run.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(file_handler)
    _run_handlers.append(file_handler)

    if verbose:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root.addHandler(console)
        _run_handlers.append(console)
    return log_path


class Heartbeat:
    """Prints and logs a still-working line while a single step runs long.

    `status` returns the current step's label and how many seconds it has run. A line
    is emitted each time a step passes another multiple of `interval`, so quick
    steps stay silent and a stalled one is reported every `interval` seconds.
    """

    def __init__(
        self,
        status: Callable[[], tuple[str, float]],
        interval: float = HEARTBEAT_SECONDS,
        poll: float | None = None,
    ):
        self._status = status
        self._interval = interval
        self._poll = poll if poll is not None else min(1.0, interval / 2)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        reported: dict[str, int] = {}
        while not self._stop.wait(self._poll):
            label, elapsed = self._status()
            intervals = int(elapsed // self._interval)
            if intervals > reported.get(label, 0):
                reported[label] = intervals
                message = f"still working on '{label}' ({format_elapsed(elapsed)} so far)"
                logger.info(message)
                print(f"    ... {message}", flush=True)

    def __enter__(self) -> "Heartbeat":
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        self._thread.join(timeout=1)


class RunTracker:
    """Prints progress, logs timings and records per-step token usage.

    Tasks run one at a time and every agent shares one LLM, so a step's usage is
    the growth of the LLM's lifetime counters since the previous step finished.
    """

    def __init__(self, llm: LLM, labels: list[str]):
        self._llm = llm
        self.labels = labels
        self._last = llm.get_token_usage_summary().model_copy()
        self._step_started = time.monotonic()
        self.usage: list[tuple[str, UsageMetrics]] = []

    @property
    def current(self) -> tuple[str, float]:
        """Label of the step now running and how long it has been running."""
        index = min(len(self.usage), len(self.labels) - 1)
        return self.labels[index], time.monotonic() - self._step_started

    def started(self) -> None:
        print(f"[0/{len(self.labels)}] Starting: {self.labels[0]}...")
        logger.info("step 1/%d '%s' started", len(self.labels), self.labels[0])

    def __call__(self, _output: TaskOutput) -> None:
        now = self._llm.get_token_usage_summary().model_copy()
        label, elapsed = self.current
        delta = now.delta_since(self._last)
        self.usage.append((label, delta))
        self._last = now
        self._step_started = time.monotonic()

        done, total = len(self.usage), len(self.labels)
        print(f"[{done}/{total}] {label} complete ({format_elapsed(elapsed)})")
        logger.info(
            "step %d/%d '%s' finished in %s (input %d, completion %d, reasoning %d, requests %d)",
            done, total, label, format_elapsed(elapsed),
            delta.prompt_tokens, delta.completion_tokens, delta.reasoning_tokens,
            delta.successful_requests,
        )
        if done < total:
            logger.info("step %d/%d '%s' started", done + 1, total, self.labels[done])
