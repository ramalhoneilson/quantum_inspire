#!/usr/bin/env python3
"""Example 6: Detached submission and job recovery via QPY serialization.

Why this matters:
  In `qiskit_quantuminspire`, calling `job.job_id()` returns an empty string.
  The provider uses `batch_job_id` under the hood, but the individual circuit
  job IDs needed to fetch results live purely on the in-memory `QIJob` object.

  If your script exits, terminal closes, or network disconnects while waiting in queue,
  you CANNOT retrieve results by batch ID alone through Qiskit's public API.
  The solution is job handle serialization:
    `job.serialize("job_handle.qpy")` -> saves the job handle to disk
    `QIJob.deserialize(provider, "job_handle.qpy")` -> restores the job handle

Usage:
    # Option A: Submit and immediately serialize handle to disk (then poll)
    python examples/06_async_serialize_poll.py

    # Option B: Submit and disconnect immediately (does NOT wait)
    python examples/06_async_serialize_poll.py --submit-only --handle my_job.qpy

    # Option C: Reconnect later and resume polling from saved handle
    python examples/06_async_serialize_poll.py --poll-only --handle my_job.qpy
"""

from __future__ import annotations

import argparse
import os
import sys
from rich.console import Console

from qi_starter.auth import get_provider
from qi_starter.circuits import create_bell_circuit
from qi_starter.results import canonicalize_counts, format_ascii_histogram
from qi_starter.runner import (
    extract_counts,
    load_job_handle,
    poll_job,
    save_job_handle,
    transpile_for_backend,
)


def main():
    parser = argparse.ArgumentParser(description="Demonstrate detached QI job submission and QPY recovery.")
    parser.add_argument("--backend", default="QX emulator", help="Target backend (default: QX emulator)")
    parser.add_argument("--shots", type=int, default=1024, help="Shots (default: 1024)")
    parser.add_argument("--handle", default="runs/latest_job.qpy", help="Path to save/load QPY handle")
    parser.add_argument("--submit-only", action="store_true", help="Submit and exit immediately without polling")
    parser.add_argument("--poll-only", action="store_true", help="Do not submit; poll an existing handle file")
    args = parser.parse_args()

    console = Console()
    console.print("\n[bold cyan]=== Asynchronous Job Serialization & Recovery ===[/bold cyan]\n")

    provider = get_provider()

    # Mode 1: Poll-only from existing serialized handle
    if args.poll_only:
        if not os.path.exists(args.handle):
            console.print(f"[bold red]Handle file '{args.handle}' does not exist.[/bold red]")
            sys.exit(1)

        console.print(f"Loading job handle from: [green]{args.handle}[/green]")
        job = load_job_handle(provider, args.handle)
        console.print(f"Restored job: Batch ID [yellow]{job.batch_job_id}[/yellow]")

        console.print("Polling job to completion...")
        result = poll_job(job, timeout=300, poll_interval=3, verbose=True)
        counts = extract_counts(result, 1)[0]
        canonical = canonicalize_counts(counts, reverse_bits=True)
        console.print("\n[bold]Retrieved Results:[/bold]")
        console.print(format_ascii_histogram(canonical))
        return

    # Mode 2: Submit and serialize
    backend = provider.get_backend(args.backend)
    qc = create_bell_circuit()
    transpiled = transpile_for_backend(qc, backend)

    console.print(f"Submitting Bell state to '{args.backend}'...")
    job = backend.run(transpiled, shots=args.shots)
    batch_id = job.batch_job_id
    console.print(f"Submitted. Provider batch ID: [yellow]{batch_id}[/yellow]")

    # Persist the handle immediately
    saved_path = save_job_handle(job, args.handle)
    console.print(f"[bold green]Serialized job handle to:[/bold green] {saved_path}")

    if args.submit_only:
        console.print("\n[yellow]Exiting without waiting (--submit-only was specified).[/yellow]")
        console.print("To poll this job later, run:")
        console.print(f"    [bold cyan]python examples/06_async_serialize_poll.py --poll-only --handle {args.handle}[/bold cyan]\n")
        return

    # Simulate waiting in a detached process: reload from disk and poll
    console.print("\nSimulating detached process recovery: reloading job from disk...")
    recovered_job = load_job_handle(provider, saved_path)
    console.print(f"Successfully recovered job [yellow]{recovered_job.batch_job_id}[/yellow]")

    console.print("Polling recovered job handle...")
    result = poll_job(recovered_job, timeout=300, poll_interval=3, verbose=True)
    counts = extract_counts(result, 1)[0]
    canonical = canonicalize_counts(counts, reverse_bits=True)

    console.print("\n[bold]Execution Results:[/bold]")
    console.print(format_ascii_histogram(canonical))
    console.print()


if __name__ == "__main__":
    main()
