#!/usr/bin/env python3
"""Example 4: Batch multiple circuits into a single Quantum Inspire job.

Demonstrates:
  - Submitting multiple distinct circuits in one batch job
  - Respecting backend batch job limits (`max_jobs_per_batch_job`)
  - Defensive count recovery per circuit index (preventing all-or-nothing crashes)

Usage:
    python examples/04_batch_submission.py
"""

from __future__ import annotations

import argparse
from rich.console import Console

from qi_starter.auth import get_provider
from qi_starter.backend import chunk_ranges, get_backend_info
from qi_starter.circuits import create_bell_circuit, create_ghz_circuit, create_grover_circuit
from qi_starter.results import canonicalize_counts, format_ascii_histogram
from qi_starter.runner import execute_circuit


def main():
    parser = argparse.ArgumentParser(description="Submit a batch of quantum circuits to Quantum Inspire.")
    parser.add_argument("--backend", default="QX emulator", help="Target backend name (default: QX emulator)")
    parser.add_argument("--shots", type=int, default=512, help="Shots per circuit (default: 512)")
    args = parser.parse_args()

    console = Console()
    console.print(f"\n[bold cyan]=== Multi-Circuit Batch Submission on '{args.backend}' ===[/bold cyan]\n")

    # Step 1: Assemble a list of different circuits
    circuits = [
        create_bell_circuit(),
        create_ghz_circuit(num_qubits=3),
        create_grover_circuit(marked_state="01"),
    ]
    labels = ["Bell State (|00>+|11>)", "3-Qubit GHZ (|000>+|111>)", "Grover Search (Target: |01>)"]

    console.print(f"Prepared {len(circuits)} circuits for submission:")
    for i, label in enumerate(labels):
        console.print(f"  [{i}] {label} ({circuits[i].num_qubits} qubits)")

    # Step 2: Query backend limits
    provider = get_provider()
    backend = provider.get_backend(args.backend)
    info = get_backend_info(backend)

    max_batch = info.get("max_jobs_per_batch_job") or 10
    console.print(f"\nBackend '{args.backend}' maximum circuits per batch job: [yellow]{max_batch}[/yellow]")

    # Check chunking
    chunks = chunk_ranges(len(circuits), max_batch)
    console.print(f"Planned chunks: {chunks}")

    # Step 3: Submit batch
    console.print(f"\nSubmitting batch of {len(circuits)} circuits ({args.shots} shots each)...")
    execution = execute_circuit(
        circuit_or_circuits=circuits,
        backend=backend,
        shots=args.shots,
        verbose=True,
    )

    counts_list = execution["counts"]
    console.print(f"\n[bold green]Batch completed in {execution['elapsed_seconds']}s. Provider Batch ID: {execution['batch_job_id']}[/bold green]\n")

    # Step 4: Display individual results
    for i, (counts, label) in enumerate(zip(counts_list, labels)):
        console.print(f"[bold underline]Result for Circuit {i}: {label}[/bold underline]")
        canonical = canonicalize_counts(counts, reverse_bits=True)
        console.print(format_ascii_histogram(canonical))
        console.print()


if __name__ == "__main__":
    main()
