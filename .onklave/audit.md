# Template audit

- **Last audited:** 2026-08-04
- **Audited by:** Onklave platform maintenance (automated, Claude Code)
- **Next review due:** 2026-11-04 (quarterly, or sooner on a dependency alert)

## Why this file exists
So we know when this template was last deliberately checked, and what was true at
the time. Apps are generated from this repo — stale or vulnerable dependencies
here propagate to every app created from it.

## Scope of this audit
- Clean-room install and test run from a fresh virtualenv (`pip install -e '.[dev]'`, `pytest`).
- Dependency currency and known-vulnerability scan of the full resolved dependency
  set (runtime + `dev` extra), using `pip-audit` and `pip list --outdated`.
- Python base image currency: built and ran the test suite on `python:3.12-slim`,
  `python:3.13-slim` and `python:3.14-slim`.
- `docker build` of the committed Dockerfile, plus runtime checks on the built
  image: effective UID, interpreter version, and real `SIGTERM` behaviour
  (`docker stop`) — the shutdown path is the failure mode that matters most for a
  long-running worker.
- Security review of the Dockerfile, `.dockerignore`, `.gitignore`, and a scan of
  the full git history for committed secrets.
- Not in scope: `onklave.yaml` (written and verified in a previous pass, left
  untouched); the worker's business logic, which is a deliberate placeholder seam.

## Verification run
| Check | Command | Result |
|---|---|---|
| Fresh venv | `python3 -m venv .venv` (Python 3.14.4 host) | Pass |
| Install | `pip install -e '.[dev]'` | Pass — resolved pytest 9.1.1, pluggy 1.6.0, packaging 26.2, pygments 2.20.0, iniconfig 2.3.0 |
| Tests | `pytest` | Pass — 9 passed in 0.06s |
| Vulnerability scan | `pip-audit` (v2.10.1) | Pass — "No known vulnerabilities found" (local `worker` dist skipped: not on PyPI) |
| Outdated check | `pip list --outdated` | Pass — no real dependency outdated (see Finding 3 for the spurious `worker` row) |
| Tests on Python 3.12 | `docker run python:3.12-slim … pytest` | Pass — 9 passed (Python 3.12.13) |
| Tests on Python 3.13 | `docker run python:3.13-slim … pytest` | Pass — 9 passed (Python 3.13.14) |
| Tests on Python 3.14 | `docker run python:3.14-slim … pytest` | Pass — 9 passed (Python 3.14.6) |
| Image build | `docker build -t tpw-audit-final .` | Pass — 204MB, Python 3.13.14 |
| Non-root runtime | `docker run --entrypoint sh … -c 'id'` | Pass — `uid=10001(worker) gid=10001(worker)` |
| Graceful shutdown | `docker stop -t 30 <container>` | Pass — logged "received SIGTERM, shutting down", exited in 0.15s with exit code 0 |
| Secrets in history | `git grep -E '(api[_-]?key\|secret\|password\|token\|BEGIN .* PRIVATE KEY\|AKIA…)' $(git rev-list --all)` | Pass — no matches in any commit |
| Install + tests after adding the major ceiling (reconciliation) | `docker run python:3.13-slim … pip install -e '.[dev]' && pytest` | Pass — resolved pytest 9.1.1, **9 passed in 0.06s** |
| Ceiling does not exclude the current release (reconciliation) | `pip index versions pytest` | Latest is 9.1.1; `>=9.1.1,<10` admits it and every future 9.x |

The last two rows are from the **cross-template reconciliation pass** (2026-08-04,
same audit date). See finding 2.

## Dependency status
The template declares **no runtime dependencies** — the worker is pure standard
library. The only declared dependency is the `dev` extra.

| Package | Before | After | Note |
|---|---|---|---|
| pytest (declared) | `>=8` | `>=9.1.1,<10` | Floor raised to the tested release, then a major ceiling added in the reconciliation pass to match `template-fastapi`'s convention. `>=8` already resolved to 9.1.1, so the floor records reality; the ceiling is the new constraint. |
| pytest (resolved) | 9.1.1 | 9.1.1 | Latest. |
| pluggy | 1.6.0 | 1.6.0 | Latest (transitive). |
| packaging | 26.2 | 26.2 | Latest (transitive). |
| pygments | 2.20.0 | 2.20.0 | Latest (transitive). |
| iniconfig | 2.3.0 | 2.3.0 | Latest (transitive). |
| Base image | `python:3.12-slim` | `python:3.13-slim` | Python 3.12 is in security-only maintenance; 3.13 is in full bugfix support. Verified by building and testing on it. |

Deliberately **not** changed:
- **Base image not moved to `python:3.14-slim`.** The suite passes on 3.14 (verified
  above), so this is a currency choice, not a compatibility one. 3.13 is the safer
  default for a template that customers extend with third-party libraries, where
  wheel availability on the newest interpreter is the common build failure. See
  Finding 1.
- **`requires-python` left at `>=3.12`.** The image is 3.13, but there is no reason
  to stop a developer running the app locally on 3.12.
- **No lockfile added.** See Finding 2 — a lockfile is a decision for the generated
  app, not for a zero-runtime-dependency template. (Major *ceilings* were added in the
  reconciliation pass; that is a weaker and cheaper control than a lockfile and does
  not replace one.)

## Findings

1. **(low) Base image is one minor version behind the current Python release.**
   The image now tracks `python:3.13-slim`. Python 3.14 is current and the suite
   passes on it, but 3.13 was chosen because generated apps add third-party
   dependencies and `-slim` has no compiler toolchain, so a package without a
   3.14 wheel would fail the build. *Action taken:* moved 3.12 → 3.13. *Recommended:*
   revisit at the next quarterly review and move to 3.14 once it is the ecosystem
   default.

2. **(low) No dependency pinning or lockfile — PARTIALLY ADDRESSED in the
   reconciliation pass.** `pyproject.toml` used floor constraints only (`pytest>=9`)
   and there is no lockfile, so two builds of the same commit can resolve different
   versions. For this template the blast radius is near zero — no runtime
   dependencies, one dev tool — and floating gets security patches for free. It stops
   being acceptable the moment a generated app takes real runtime dependencies.
   *Action originally taken:* none.
   *Action taken in the reconciliation pass:* `template-fastapi` was audited
   independently on the same date and adopted **floor + major ceiling**
   (`fastapi>=0.141.1,<1.0`, `pytest>=9.1.1,<10`) with an explanatory comment, while
   this template kept a bare floor. Two Python templates teaching two different
   dependency conventions is the kind of drift that propagates into every generated
   app, so this one was aligned to the stricter of the two: `pytest>=9.1.1,<10`, with
   the same comment. The ceiling does not undercut the "floating gets patches for
   free" argument above — patch and minor releases, which is where security fixes
   ship, still flow in automatically; only an unreviewed *major* is blocked. Re-ran
   the suite after the change: 9 passed.
   *Still recommended:* generated apps that add real runtime dependencies should
   adopt a lockfile (`uv.lock`, `pip-tools`, or a `constraints.txt`) and a
   `--require-hashes` install in the Dockerfile. A major ceiling is not a lockfile.

3. **(low) Distribution name `worker` collides with an unrelated package on PyPI.**
   `pip list --outdated` reports `worker 0.1.0 → 2018.4.1` because a package literally
   named `worker` exists publicly. Nothing installs it today (the project is installed
   from the local path), but the collision is the shape of a dependency-confusion
   problem if anything ever resolves `worker` by name from an index. *Action taken:*
   none — renaming would change the console-script name and the module path, which is
   a template-identity decision, not an audit fix. *Recommended:* namespace the
   distribution (e.g. `onklave-worker`, keeping the `worker` import package) when the
   template is next revised.

4. **(low) Shutdown waits for the in-flight tick.** Signal handling itself is correct
   and was verified end-to-end against a real container: the process runs as PID 1,
   installs its own `SIGTERM`/`SIGINT` handlers, uses an interruptible
   `Event.wait()` for the interval, and exited in 0.15s with code 0 on `docker stop`.
   The residual risk is in the seam customers replace: if `do_work()` runs longer than
   the platform's termination grace period, the container will be `SIGKILL`ed
   mid-tick. *Action taken:* documented the constraint and the fix (thread the stop
   event into the job and check it at a safe point) in the README's new "Graceful
   shutdown" section.

5. **(none) No secrets committed.** A regex sweep across every commit in the
   repository's history (`git rev-list --all`) for API keys, passwords, tokens, PEM
   private-key headers and AWS access-key IDs returned no matches. The history is
   five commits of template scaffolding only.

6. **(none) Container hardening is already correct.** Dependencies are installed as
   root into system site-packages and the process then drops to a dedicated
   `uid=10001` non-root user, so the running worker cannot modify its own code.
   `PYTHONDONTWRITEBYTECODE` and `--no-cache-dir` keep the layer clean, and no
   inbound port is exposed. No change needed.

7. **(none) `.dockerignore` is correct.** The Dockerfile copies an explicit
   allowlist (`pyproject.toml`, `README.md`, `src/`) rather than `COPY . .`, so build
   context leakage is structurally impossible today. Secret patterns were still added
   as defence in depth, because a generated app that switches to `COPY . .` — a very
   likely edit — would otherwise silently ship a local `.env` into an image layer.

## Changes made in this audit
- Dockerfile: base image `python:3.12-slim` → `python:3.13-slim`.
- `pyproject.toml`: `dev` extra floor `pytest>=8` → `pytest>=9`; dropped the now-stale
  "(Python 3.12)" from the project description. Then, in the cross-template
  reconciliation pass (finding 2): `pytest>=9` → `pytest>=9.1.1,<10`, plus the
  floor/ceiling rationale comment, adopting `template-fastapi`'s convention so the two
  Python templates teach the same dependency-constraint style. Tests re-run green
  (9 passed) on `python:3.13-slim` after the change.
- `.dockerignore`: added `.env`, `.env.*`, `*.pem`, `*.key`.
- `.gitignore`: added `.env`, `.env.*`, `*.pem`, `*.key`.
- `README.md`: replaced the hardcoded "Python 3.12" framing with a supported-version
  line, and added a "Graceful shutdown" section covering the PID 1 / grace-period
  constraint on long-running ticks.
- Added this file.

## Open items
- Decide whether to move the base image to `python:3.14-slim` at the next review;
  the test suite already passes on it, so this is purely a judgement call about
  third-party wheel availability for generated apps.
- Decide whether to rename the distribution away from the PyPI-colliding name
  `worker` (Finding 3). This changes the console-script name, so it needs a human.
- **Bump the `pytest` floor when the ceiling is next reviewed.** `>=9.1.1,<10` is
  correct today; the point of the ceiling is that a human sees pytest 10 before it
  lands, so this needs the quarterly review to actually happen (it is the same
  automation gap noted across the template fleet).
- No action required on `onklave.yaml` — deliberately untouched, verified previously.
