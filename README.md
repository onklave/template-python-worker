# template-python-worker

An Onklave project template: a clean, containerised **Python background
worker**. It runs a loop on a fixed interval, does a unit of work each tick, and
shuts down cleanly on `SIGTERM`/`SIGINT`. It exposes **no inbound port** — it is
a worker, not a service.

Requires Python 3.12 or newer; the container image is built on `python:3.13-slim`.

## What it is

- A long-running background process (`python -m worker.main`).
- Env-driven config, structured logging to stdout, graceful shutdown.
- The per-tick work lives in `do_work()` in `src/worker/main.py` — that is the
  seam you replace with your real job (poll a queue, process a batch, etc.).

## Configuration

| Variable                  | Default | Description                     |
| ------------------------- | ------- | ------------------------------- |
| `WORKER_INTERVAL_SECONDS` | `30`    | Seconds between ticks (> 0).    |
| `LOG_LEVEL`               | `INFO`  | Python log level name.          |

## Run locally

```bash
pip install -e .
python -m worker.main
```

Stop it with `Ctrl+C` — it exits cleanly, no traceback.

## Graceful shutdown

The process runs as PID 1 in the container and installs its own `SIGTERM` /
`SIGINT` handlers, so an orchestrator's stop signal is honoured instead of being
ignored (an ignored `SIGTERM` means `SIGKILL` and lost in-flight work). The
interval sleep is interruptible, so an idle worker exits in milliseconds.

One thing to keep in mind when you replace `do_work()`: shutdown waits for the
**current tick to finish**. If your job can run longer than the platform's
termination grace period, check the stop event inside your own work — pass it in
and bail out at a safe point — rather than relying on the loop boundary.

## Test

```bash
pip install -e '.[dev]'
pytest
```

Or use the `Makefile` targets: `make install`, `make run`, `make test`.

## How Onklave runs it

Onklave reads **`onklave.yaml`** at the repo root — that is where this service is
declared (GitHub Actions is not used). It builds the repo from the `Dockerfile`
and runs the resulting image as a background **worker**: `onklave.yaml` sets
`expose.enabled: false` with no port or health path, because this process serves
no HTTP. The container runs as a non-root user and starts with
`python -m worker.main`. Configure behaviour through environment variables (see
the table above).
