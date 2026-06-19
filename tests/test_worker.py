"""Tests for the worker tick/work function and config."""

import threading

import pytest

from worker.main import Config, do_work, run


def test_do_work_returns_tick():
    assert do_work(1) == 1
    assert do_work(42) == 42


def test_config_from_env_defaults():
    config = Config.from_env({})
    assert config.interval_seconds == 30.0
    assert config.log_level == "INFO"


def test_config_from_env_overrides():
    config = Config.from_env(
        {"WORKER_INTERVAL_SECONDS": "0.01", "LOG_LEVEL": "debug"}
    )
    assert config.interval_seconds == 0.01
    assert config.log_level == "DEBUG"


@pytest.mark.parametrize("bad", ["", "abc", "0", "-5"])
def test_config_rejects_bad_interval(bad):
    with pytest.raises(ValueError):
        Config.from_env({"WORKER_INTERVAL_SECONDS": bad})


def test_run_stops_when_event_set():
    config = Config.from_env({"WORKER_INTERVAL_SECONDS": "0.01"})
    stop = threading.Event()

    # Stop after a short delay so the loop runs a few ticks then exits.
    timer = threading.Timer(0.05, stop.set)
    timer.start()
    try:
        ticks = run(config, stop)
    finally:
        timer.cancel()

    assert ticks >= 1


def test_run_exits_immediately_if_already_stopped():
    config = Config.from_env({"WORKER_INTERVAL_SECONDS": "0.01"})
    stop = threading.Event()
    stop.set()
    assert run(config, stop) == 0
