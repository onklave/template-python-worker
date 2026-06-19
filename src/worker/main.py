"""Onklave background worker.

A long-running background worker with no inbound port. It wakes on a fixed
interval, does a unit of work, and exits cleanly on SIGTERM/SIGINT.

Run locally:
    python -m worker.main

Configuration (environment variables):
    WORKER_INTERVAL_SECONDS  Seconds between ticks (default: 30)
    LOG_LEVEL                Python log level name (default: INFO)
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from dataclasses import dataclass

logger = logging.getLogger("worker")


@dataclass(frozen=True)
class Config:
    """Runtime configuration resolved from the environment."""

    interval_seconds: float
    log_level: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = os.environ if env is None else env
        raw_interval = env.get("WORKER_INTERVAL_SECONDS", "30")
        try:
            interval = float(raw_interval)
        except ValueError:
            raise ValueError(
                f"WORKER_INTERVAL_SECONDS must be a number, got {raw_interval!r}"
            )
        if interval <= 0:
            raise ValueError("WORKER_INTERVAL_SECONDS must be greater than 0")
        return cls(
            interval_seconds=interval,
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
        )


def configure_logging(level: str) -> None:
    """Configure structured-ish line logging to stdout."""
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def do_work(tick: int) -> int:
    """Perform a single unit of work for the given tick.

    This is the testable seam of the worker: replace the body with the real
    job (poll a queue, process a batch, etc.) and return whatever the run loop
    should treat as the result of this tick.
    """
    logger.info("tick %d: doing work", tick)
    return tick


def run(config: Config, stop: threading.Event) -> int:
    """Run the worker loop until ``stop`` is set. Returns the tick count."""
    logger.info(
        "worker starting (interval=%ss, log_level=%s)",
        config.interval_seconds,
        config.log_level,
    )
    tick = 0
    while not stop.is_set():
        tick += 1
        try:
            do_work(tick)
        except Exception:  # noqa: BLE001 - keep the loop alive on tick errors
            logger.exception("tick %d failed", tick)
        # Interruptible sleep: wakes immediately when stop is set.
        stop.wait(config.interval_seconds)
    logger.info("worker stopped cleanly after %d tick(s)", tick)
    return tick


def main(argv: list[str] | None = None) -> int:
    config = Config.from_env()
    configure_logging(config.log_level)

    stop = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:
        logger.info("received %s, shutting down", signal.Signals(signum).name)
        stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    run(config, stop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
