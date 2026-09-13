# Quantum Inspire Starter & Python Infrastructure

A beginner-friendly, production-tested guide and Python infrastructure for running quantum circuits on **Quantum Inspire** (QuTech / TU Delft).

This repository provides clear step-by-step instructions, runnable Python scripts, and hardened execution patterns learned from large-scale quantum software experimentation in [Quanifi](https://github.com/ramalhoneilson/quanifi) — including hardware basis gate fixes, asynchronous job serialization, batch partitioning, and defensive result recovery.

---

## Table of Contents
1. [What is Quantum Inspire?](#what-is-quantum-inspire)
2. [Step 1: Prepare the Environment](#step-1-prepare-the-environment)
3. [Step 2: Install Dependencies](#step-2-install-dependencies)
4. [Step 3: Authenticate & Login](#step-3-authenticate--login)
5. [Step 4: Check Connection & Available Backends](#step-4-check-connection--available-backends)
6. [Step 5: Run Your First Circuit (Bell State)](#step-5-run-your-first-circuit-bell-state)
7. [Step 6: Run a Complete Algorithm (Grover Search)](#step-6-run-a-complete-algorithm-grover-search)
8. [Step 7: Batch Submissions & Chunking](#step-7-batch-submissions--chunking)
9. [Step 8: Hard-Won Production Lessons from Quanifi](#step-8-hard-won-production-lessons-from-quanifi)
   - [The Tuna-17 `rx` Gate Hardware Defect](#1-the-tuna-17-rx-gate-hardware-defect)
   - [Asynchronous Job Persistence via QPY Serialisation](#2-asynchronous-job-persistence-via-qpy-serialisation)
   - [Defensive Per-Index Result Extraction](#3-defensive-per-index-result-extraction)
   - [Bit Endianness Normalisation (q0-right vs q0-left)](#4-bit-endianness-normalisation-q0-right-vs-q0-left)
   - [Hardware Quota Safety Guard (`--armed`)](#5-hardware-quota-safety-guard---armed)
10. [Step 9: Presenting & Analyzing Results](#step-9-presenting--analyzing-results)
11. [Project Structure](#project-structure)
12. [Running Automated Tests](#running-automated-tests)

---

## What is Quantum Inspire?

[Quantum Inspire](https://www.quantum-inspire.com/) is QuTech's cloud platform for quantum computing. It provides access to:
- **Noiseless & Noisy Emulators**:
  - `QX emulator`: 10-qubit high-performance simulator (free, fast, ideal for development and functional testing).
  - `Ry emulator`: 9-qubit emulator.
- **Physical Superconducting Quantum Processors (QPUs)**:
  - `Tuna-5`: 5-qubit superconducting transmon chip.
  - `Tuna-9`: 9-qubit superconducting transmon chip.
  - `Tuna-17`: 17-qubit superconducting transmon chip with surface code layout.

---

## Step 1: Prepare the Environment & Install with `uv`

This project uses [`uv`](https://github.com/astral-sh/uv), the blazing-fast Python package and project manager.

If you don't have `uv` installed:
```bash
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# or with Homebrew:
brew install uv
```

To initialize the environment and install all dependencies (including testing and visualization extras), simply run:
```bash
cd /Users/neilson/projects/quantum_inspire
uv sync --all-extras
```

`uv sync` automatically:
1. Creates a local `.venv` environment using Python 3.12 (or your preferred installed Python).
2. Resolves and freezes exact compatible versions in `uv.lock`.
3. Installs `qiskit`, `qiskit-quantuminspire`, `quantuminspire`, and the local `qi_starter` package in editable mode.

> [!TIP]
> With `uv`, you don't even need to remember to run `source .venv/bin/activate`! You can execute any script directly using `uv run python examples/...`.

*(Optional: If you ever need to use classic `pip` instead, run `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`)*

---

## Step 3: Authenticate & Login

Quantum Inspire 4.x uses browser-based OAuth authentication.

1. Run the login command from your terminal:
   ```bash
   qi login
   ```
2. Your default web browser will open to the Quantum Inspire sign-in portal.
3. Log in with your Quantum Inspire account credentials and authorize the CLI.
4. Your terminal will confirm:
   ```text
   Successfully logged in to https://api.quantum-inspire.com
   ```
5. Tokens are saved locally to `~/.quantuminspire/config.json`.

> [!TIP]
> If your session ever expires or you encounter token refresh errors, force a re-login with:
> ```bash
> qi login --force
> ```

---

## Step 4: Check Connection & Available Backends

Verify that Python can read your credentials and list visible backends:

```bash
uv run python examples/01_check_connection.py
```

Expected output:
```text
=== Quantum Inspire Connection & Account Check ===

✅ Credentials file found at: ~/.quantuminspire/config.json
   Default Host: https://api.quantum-inspire.com
   Refresh Token Expiry: 2026-10-13T02:00:00+00:00 (Active)

Connecting to Quantum Inspire API...
✅ Successfully authenticated via QIProvider!

Available Quantum Inspire Backends:
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ Name        ┃ Type         ┃ Qubits ┃ Max Shots ┃ Max Batch ┃ Status  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ QX emulator │ Emulator     │ 10     │ 2048      │ 10        │ IDLE    │
│ Tuna-5      │ Hardware QPU │ 5      │ 131072    │ 5         │ OFFLINE │
│ Ry emulator │ Emulator     │ 9      │ 1024      │ 10        │ IDLE    │
│ Tuna-9      │ Hardware QPU │ 9      │ 131072    │ 5         │ OFFLINE │
│ Tuna-17     │ Hardware QPU │ 17     │ 131072    │ 5         │ IDLE    │
└━━━━━━━━━━━━━┴━━━━━━━━━━━━━━┴━━━━━━━━┴━━━━━━━━━━━┴━━━━━━━━━━━┴━━━━━━━━━┘
```

You can also list backends directly from the command line anytime with:
```bash
uv run qi backends list
```

---

## Step 5: Run Your First Circuit (Bell State)

Run a 2-qubit entangled Bell state ($|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt{2}}$) on the free `QX emulator`:

```bash
uv run python examples/02_run_bell_state.py
```

Expected output:
```text
=== Bell State on 'QX emulator' ===

1. Creating Bell state circuit (|00> + |11>) / sqrt(2)...
     ┌───┐     ┌─┐   
q_0: ┤ H ├──■──┤M├───
     └───┘┌─┴─┐└╥┘┌─┐
q_1: ─────┤ X ├─╫─┤M├
          └───┘ ║ └╥┘
c: 2/═══════════╩══╩═
                0  1 

2. Submitting circuit (1024 shots)...
Transpiling 1 circuit(s) for QX emulator...
Submitting 1 circuit(s) to 'QX emulator' (1024 shots)...
Submitted. Provider batch job ID: 12345
Polling job 12345 (timeout=300s, interval=3s)...
  Status: RUNNING
  Status: DONE
  Job completed successfully.

Execution completed in 4.12s
Raw Qiskit counts (q0-right): {'00': 508, '11': 516}

Normalized Results (canonical q0-left):
  |00> :   508 ( 49.61%) [███████████████████████████████████]
  |11> :   516 ( 50.39%) [████████████████████████████████████]

Combined |00> + |11> probability: 100.00%
```

---

## Step 6: Run a Complete Algorithm (Grover Search)

Grover's algorithm searches an unsorted database of $N = 2^n$ items in $\mathcal{O}(\sqrt{N})$ time.
For $n=2$ qubits (4 basis states) and a single marked item, 1 iteration produces a **theoretically exact 100% success probability**.

Run Grover search targeting state $|10\rangle$:
```bash
uv run python examples/03_run_grover_search.py --marked 10 --shots 1024
```

Expected output:
```text
=== 2-Qubit Grover Search (Target: |10>) on 'QX emulator' ===

1. Building Grover search circuit with oracle marked for |10>...
2. Executing algorithm (1024 shots)...
Submitting 1 circuit(s) to 'QX emulator' (1024 shots)...
Submitted. Provider batch job ID: 12346
Polling job 12346 (timeout=300s, interval=3s)...
  Status: DONE
  Job completed successfully.

Execution Results:
  |10> :  1024 (100.00%) [███████████████████████████████████]

Target State Analysis (|10>):
  Successes: 1024/1024
  Success Probability: 100.00%
  95% Wilson Confidence Interval: [99.64%, 100.00%]
  Hellinger Distance to Exact Ideal: 0.0000 (0.0 = perfect match)
```

---

## Step 7: Batch Submissions & Chunking

Quantum Inspire supports submitting multiple circuits in a single batch job:
```python
job = backend.run([circuit_a, circuit_b, circuit_c], shots=1024)
```

Run the batch demonstration:
```bash
uv run python examples/04_batch_submission.py
```

### Batch Chunking
Each backend enforces a limit on the number of circuits per batch job:
```python
max_jobs = backend.get_backend_type().max_jobs_per_batch_job
```
- `QX emulator`: up to 10 circuits per batch job.
- `Tuna-17`: up to 5 circuits per batch job.

If you have 20 circuits, use `chunk_ranges(len(circuits), limit)` from `qi_starter.backend` to partition them into sequential slices `[(0, 5), (5, 10), (10, 15), (15, 20)]`.

---

## Step 8: Hard-Won Production Lessons from Quanifi

During the development of Quanifi's Grover hardware evaluation on Quantum Inspire, several vendor-specific behaviors and platform edge-cases were discovered and resolved:

### 1. The Tuna-17 `rx` Gate Hardware Defect
- **The Problem**: `Tuna-17` advertises `rx` in its gateset. However, experimental verification revealed that Tuna-17 executes `rx` as though the rotation angle were **negated** ($-\theta$). Circuits transpiled with `rx` return the bitwise complement of the marked state!
- **The Solution**: The physical hardware gateset natively implements `CZ` for 2-qubit operations and `Ry`, `Rz` for 1-qubit operations. `Ry` and `Rz` are fully calibrated and sound, and together span all single-qubit rotations.
- **Implementation**: `qi_starter.backend.native_basis_gates(backend)` automatically filters out `rx`:
  ```python
  _QI_UNRELIABLE_GATES = {"rx"}
  basis = sorted(mapped_device_gates - _QI_UNRELIABLE_GATES)
  # Qiskit transpile with basis_gates=basis synthesizes with Ry and Rz!
  ```
- Run the safe hardware script to inspect the transpiled output:
  ```bash
  # Preflight inspection (zero quota spent):
  uv run python examples/05_hardware_tuna17_safe.py

  # Real hardware execution:
  uv run python examples/05_hardware_tuna17_safe.py --armed
  ```

### 2. Asynchronous Job Persistence via QPY Serialisation
- **The Problem**: In `qiskit_quantuminspire`, `job.job_id()` returns `""`. The provider assigns `job.batch_job_id`, but the internal per-circuit job IDs needed to call `job.result()` live **only on the in-memory Python object**. If your script terminates or a pipeline worker restarts, the job is unpollable through the public API with just the batch ID!
- **The Solution**: Serialize the `QIJob` handle immediately after submission:
  ```python
  from qi_starter.runner import save_job_handle, load_job_handle

  # Immediately after submitting:
  save_job_handle(job, "runs/my_job.qpy")

  # Later, in a separate process or after restarting:
  job = load_job_handle(provider, "runs/my_job.qpy")
  result = job.result()
  ```
- Run the demonstration:
  ```bash
  # Submit and exit immediately without waiting:
  uv run python examples/06_async_serialize_poll.py --submit-only --handle runs/task.qpy

  # Check in later and retrieve results:
  uv run python examples/06_async_serialize_poll.py --poll-only --handle runs/task.qpy
  ```

### 3. Defensive Per-Index Result Extraction
- **The Problem**: Calling `result.get_counts()` without arguments raises an immediate exception if *even one* experiment in a multi-circuit batch failed or timed out on the provider side. This would crash your program and throw away all the successful circuit results!
- **The Solution**: Always extract counts per-index:
  ```python
  counts_list = []
  for i in range(num_circuits):
      try:
          counts_list.append(result.get_counts(i))
      except Exception:
          counts_list.append({})  # preserve successful sibling circuits
  ```

### 4. Bit Endianness Normalisation (q0-right vs q0-left)
- Qiskit and Quantum Inspire return measurement bitstrings in little-endian order (qubit 0 is the rightmost character).
- In textbook algorithms and Quanifi's canonical convention, qubit 0 is the leftmost character.
- Use `canonicalize_counts(counts, reverse_bits=True)` to convert between representations.

### 5. Hardware Quota Safety Guard (`--armed`)
- Physical QPUs (`Tuna-5`, `Tuna-9`, `Tuna-17`) consume limited research quota and cost money/credits.
- All example scripts and runner functions default to free emulators. Submitting to real hardware requires the explicit `armed=True` parameter or `--armed` CLI flag.

---

## Step 9: Presenting & Analyzing Results

The `qi_starter.results` module includes standard statistical analysis tools:

```python
from qi_starter.results import (
    canonicalize_counts,
    compute_probabilities,
    wilson_interval,
    hellinger_distance,
    format_ascii_histogram,
)

# 1. Endianness reversal
canonical = canonicalize_counts(raw_counts, reverse_bits=True)

# 2. Normalized probabilities
probs = compute_probabilities(canonical)

# 3. 95% Wilson confidence intervals
lower, upper = wilson_interval(successes=945, total=1000, confidence=0.95)
print(f"Success: 94.5% [{lower*100:.2f}%, {upper*100:.2f}%]")

# 4. Hellinger distance vs ideal
h = hellinger_distance(probs, {"10": 1.0})

# 5. Terminal ASCII histogram
print(format_ascii_histogram(canonical))
```

---

## Project Structure

```text
quantum_inspire/
├── pyproject.toml              # Project metadata & dependencies
├── requirements.txt            # Pip requirements file
├── README.md                   # Beginner guide & documentation
├── LICENSE                     # Apache 2.0 License
├── .gitignore                  # Git ignore rules
│
├── qi_starter/                 # Core Python infrastructure package
│   ├── __init__.py             # Public API exports
│   ├── auth.py                 # Offline auth check & QIProvider loader
│   ├── backend.py              # Backend discovery & Tuna-17 rx basis gate fix
│   ├── circuits.py             # Bell, GHZ, and Grover circuit generators
│   ├── runner.py               # Preflight checks, QPY serialization & polling
│   └── results.py              # Endianness, Wilson intervals & ASCII histogram
│
├── examples/                   # Step-by-step beginner scripts
│   ├── 01_check_connection.py  # Check credentials and list backends
│   ├── 02_run_bell_state.py    # Run Bell state on QX emulator
│   ├── 03_run_grover_search.py # Run Grover algorithm with Wilson interval
│   ├── 04_batch_submission.py  # Multi-circuit batch submission & chunking
│   ├── 05_hardware_tuna17_safe.py # Safe hardware run with gate fixes & --armed
│   └── 06_async_serialize_poll.py # Detached run with QPY handle save/restore
│
└── tests/                      # Automated unit test suite
    ├── test_circuits.py        # Circuit construction tests
    ├── test_backend.py         # Batch chunking & basis gate filter tests
    └── test_results.py         # Statistical calculations & formatting tests
```

---

## Running Automated Tests

Run the test suite with `pytest`:

```bash
# Using uv:
uv run pytest tests/ -v

# Or in an active virtualenv:
pytest tests/ -v
```

All tests run locally in under 2 seconds without requiring network calls or Quantum Inspire quota.
