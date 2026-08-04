# template-python-worker

An Onklave project template: a clean, containerised **Python 3.12 background
worker**. It runs a loop on a fixed interval, does a unit of work each tick, and
shuts down cleanly on `SIGTERM`/`SIGINT`. It exposes **no inbound port** — it is
a worker, not a service.

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
