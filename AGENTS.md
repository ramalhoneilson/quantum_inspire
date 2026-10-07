# AGENTS.md

Guidance for AI coding agents (Codex, Claude Code, Copilot, Cursor, Gemini and similar) working in this repository. `CLAUDE.md` contains the same guidance; keep the two files in sync when you change either.

## What this repository is

A beginner guide (`README.md`) plus a small Python package, `qi_starter`, for running Qiskit circuits on [Quantum Inspire](https://www.quantum-inspire.com/) (QuTech / TU Delft) through the `qiskit-quantuminspire` provider. The `examples/` scripts walk through the README steps one by one.

Backends you will see:
- **Emulators** (free): `QX emulator`, `Ry emulator`.
- **Real QPUs** (limited quota): `Tuna-5`, `Tuna-9`, `Tuna-17`.

Which backends an account can use varies; `uv run qi backends list` shows them.

## Safety rules (read first)

1. **Never submit to real hardware on your own initiative.** Do not pass `--armed` to an example script, do not call `execute_circuit(..., armed=True)`, and do not call `backend.run(...)` on a `Tuna-*` backend unless the human has explicitly asked for that specific hardware run in the current conversation. Hardware quota is limited and shared. Running `examples/05_hardware_tuna17_safe.py` *without* `--armed` is a preflight only and spends no quota.
2. **Never read, print, copy or commit credentials.** `qi login` stores OAuth tokens in `~/.quantuminspire/config.json`. Only `qi_starter.auth.check_auth_status()` should touch that file, and it reports only presence, host and expiry. Never paste its token fields into code, logs, issues or commits.
3. **Prefer the unit tests over live runs.** The tests need no network, no account and no quota. The example scripts need a logged-in account and network access even on the emulator; run them only when the human asks.
4. **Do not commit job handles or run output.** `*.qpy`, `runs/` and `out/` are git-ignored on purpose.

## Setup and commands

The project uses [`uv`](https://github.com/astral-sh/uv) and a committed `uv.lock`. Python 3.10–3.13 is supported.

```bash
uv sync --all-extras                 # create .venv and install everything (incl. pytest, matplotlib)
uv run pytest tests/ -v              # unit tests: offline, a few seconds
uvx ruff check .                     # lint; rules are set in pyproject.toml (ruff runs via uvx)

qi login                             # one-time browser OAuth login (human step)
qi login --force                     # re-login when the refresh token has expired
uv run qi backends list              # list backends visible to the account

uv run python examples/01_check_connection.py      # credentials + backend table
uv run python examples/02_run_bell_state.py        # Bell state on QX emulator
uv run python examples/03_run_grover_search.py --marked 10 --shots 1024
uv run python examples/04_batch_submission.py      # 3 circuits in one batch job
uv run python examples/05_hardware_tuna17_safe.py  # hardware PREFLIGHT only (no --armed!)
uv run python examples/06_async_serialize_poll.py --submit-only --handle runs/task.qpy
uv run python examples/06_async_serialize_poll.py --poll-only  --handle runs/task.qpy
```

pip fallback: `pip install -r requirements.txt` (runtime) or `pip install -r requirements-dev.txt` (runtime + pytest + matplotlib).

`qi login` opens a browser, so an agent cannot complete it. If an example fails with "No Quantum Inspire credentials found" or "refresh token expired", ask the human to run `qi login` / `qi login --force`.

## Repository layout

```text
qi_starter/
  __init__.py   public API; every exported name is listed in __all__
  auth.py       check_auth_status() (offline config check), get_provider() (QIProvider with friendly errors)
  backend.py    is_hardware(), native_basis_gates(), chunk_ranges(), get_backend_info(), describe_backends()
  circuits.py   create_bell_circuit(), create_ghz_circuit(n), create_grover_circuit("10")
  runner.py     transpile_for_backend(), execute_circuit(), poll_job(), save_job_handle(),
                load_job_handle(), extract_counts()
  results.py    canonicalize_counts(), compute_probabilities(), wilson_interval(),
                hellinger_distance(), format_ascii_histogram()
examples/       numbered, runnable walkthrough scripts (01–06), matching the README steps
tests/          offline pytest suite (test_backend.py, test_circuits.py, test_results.py)
pyproject.toml  metadata, dependencies, hatchling build (packages only qi_starter)
requirements.txt / requirements-dev.txt   pip equivalents of the pyproject dependencies
uv.lock         committed lockfile
```

`examples/` is not part of the installed package; the scripts import `qi_starter` from the editable install.

## Quantum Inspire behaviors the code relies on

Keep these in mind when changing or extending the code; each one has caused real failures.

- **Job IDs.** In `qiskit_quantuminspire`, `job.job_id()` returns `""`. Use `job.batch_job_id`. The per-circuit job IDs needed by `job.result()` exist only on the in-memory `QIJob`, so a job cannot be resumed from the batch ID alone. Call `save_job_handle(job, path)` right after `backend.run(...)` and `load_job_handle(provider, path)` to resume in another process.
- **Partial batch failures.** `result.get_counts()` with no index raises if any circuit in the batch failed. Always go through `extract_counts(result, n)`, which reads `get_counts(i)` per index and returns `{}` for failed circuits.
- **Batch limits.** Each backend caps circuits per batch job (`backend.get_backend_type().max_jobs_per_batch_job`; for example 10 on QX emulator, 5 on Tuna-17). `execute_circuit` raises `ValueError` when exceeded; split work with `chunk_ranges(count, limit)` and submit chunks sequentially. Shots are capped by `backend.max_shots`.
- **Native gates.** The provider's default target advertises gates the chip does not implement natively (e.g. CX/SWAP on Tuna-17, which uses CZ). `transpile_for_backend` therefore transpiles to `native_basis_gates(backend)`, the device gateset mapped to Qiskit names via `_QI_GATESET_TO_QISKIT`. If a backend reports a gate name missing from that table, add the mapping there rather than special-casing callers.
- **Bit order.** Qiskit and Quantum Inspire return bitstrings with qubit 0 as the **rightmost** character. This repo's printed results and `create_grover_circuit(marked_state)` use the textbook order, qubit 0 **leftmost**. Convert with `canonicalize_counts(counts, reverse_bits=True)` before comparing against a marked state or ideal distribution.
- **Hardware detection.** `is_hardware(name)` treats any backend whose name does not contain `emulator`, `simulator` or `qx` as real hardware. This errs on the safe side: an unknown backend requires `armed=True`. Do not loosen it.

## Errors raised by `qi_starter`

| Error | Raised by | Meaning |
|---|---|---|
| `RuntimeError` | `get_provider()` | SDK not installed, no credentials, expired refresh token, or provider connection failed. The message says which and what to run. |
| `PermissionError` | `execute_circuit()` | Hardware backend without `armed=True`. Do not "fix" this by adding `armed=True`; ask the human. |
| `ValueError` | `execute_circuit()` | Too many shots or too many circuits for the backend. |
| `ValueError` | `create_ghz_circuit`, `create_grover_circuit` | Invalid qubit count or marked state. |
| `TimeoutError` | `poll_job()` | Job not finished within `timeout` (default 300 s). Hardware queues can exceed this; resume later from a saved `.qpy` handle instead of resubmitting. |
| `RuntimeError` | `poll_job()` | Job ended in `ERROR` or `CANCELLED`. |

## Code conventions

- Start modules with a one-line docstring and `from __future__ import annotations`.
- Type hints use `typing` (`Dict`, `List`, `Optional`, `Tuple`, `Union`, `Any`); keep that style for consistency, since Python 3.10 is supported.
- Public functions get Google-style docstrings with `Args:`, `Returns:` and, where relevant, `Raises:`.
- Import `qiskit_quantuminspire` lazily inside the functions that need it (see `get_provider`, `load_job_handle`), so `check_auth_status` and the unit tests work without contacting the service.
- Backend objects are accessed defensively with `getattr(...)` because provider versions differ (for example `max_shots` may be an attribute or a method). Follow the same pattern.
- New public helpers must be exported from `qi_starter/__init__.py` and added to `__all__`.
- Keep wording in docs, docstrings and CLI output plain and factual: no hype, no emojis, American spelling.

### Adding an example script

- Name it `examples/NN_short_name.py` with the next free number, a `#!/usr/bin/env python3` shebang, and a module docstring with "Demonstrates:" and "Usage:" sections.
- Use `argparse` with `--backend` defaulting to `"QX emulator"` and `--shots`; print with `rich.console.Console`.
- Get the provider with `get_provider()` and submit with `execute_circuit(...)`, so the hardware guard and limit checks apply. Any script that can target hardware must require an `--armed` flag and pass it through as `armed=`.
- Add it to the README (a step or lesson, plus the Project Structure tree) and to the layout section of this file and `CLAUDE.md`.

### Changing dependencies

`qiskit-quantuminspire` constrains Qiskit (currently `qiskit>=2.0.0,<2.4.0`); Qiskit 1.x or a newer unsupported 2.x breaks the provider imports. When changing a dependency, update `pyproject.toml`, `requirements.txt` (and `requirements-dev.txt` for dev/visual extras) together, then run `uv lock` and commit `uv.lock`.

## Tests

- Tests must stay offline: no `get_provider()`, no network, no quota. Mock backends with small classes, as `tests/test_backend.py` does for `native_basis_gates`.
- Add or update tests for any change to `qi_starter`; run `uv run pytest tests/ -v` before finishing.
- To check a circuit's behavior without the service, use a local simulator (`qiskit.quantum_info.Statevector` or a local sampler) inside the test rather than a Quantum Inspire backend.

## Helping a user who is new to Quantum Inspire

- Walk them through the README in order: install with `uv sync --all-extras`, `qi login`, then `examples/01_check_connection.py`.
- Develop and debug on `QX emulator`. Move to `Tuna-*` hardware only when they ask, starting with the preflight (no `--armed`) to show the transpiled depth and two-qubit gate count.
- For long hardware queues, recommend `examples/06_async_serialize_poll.py --submit-only` and polling later from the saved handle.
- When explaining results, remember the bit-order convention above, and use `wilson_interval` for error bars on success probabilities.
