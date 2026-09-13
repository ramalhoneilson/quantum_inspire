#!/usr/bin/env python3
"""Example 2: Run a 2-qubit Bell state on the QX emulator.

Demonstrates:
  - Creating a basic entangled Bell state
  - Submitting to the free QX emulator
  - Handling endianness (q0-right vs q0-left)
  - Displaying results with an ASCII histogram

Usage:
    python examples/02_run_bell_state.py [--shots 1024]
"""

from __future__ import annotations

import argparse
from rich.console import Console

from qi_starter.auth import get_provider
from qi_starter.circuits import create_bell_circuit
from qi_starter.results import (
    canonicalize_counts,
    compute_probabilities,
    format_ascii_histogram,
)
from qi_starter.runner import execute_circuit


def main():
    parser = argparse.ArgumentParser(description="Run a Bell state circuit on Quantum Inspire.")
    parser.add_argument("--backend", default="QX emulator", help="Target backend name (default: QX emulator)")
    parser.add_argument("--shots", type=int, default=1024, help="Number of measurement shots (default: 1024)")
    args = parser.parse_args()

    console = Console()
    console.print(f"\n[bold cyan]=== Bell State on '{args.backend}' ===[/bold cyan]\n")

    # Step 1: Create circuit
    console.print("1. Creating Bell state circuit (|00> + |11>) / sqrt(2)...")
    qc = create_bell_circuit()
    console.print(f"[dim]{qc.draw(output='text')}[/dim]\n")

    # Step 2: Get backend provider
    provider = get_provider()
    backend = provider.get_backend(args.backend)

    # Step 3: Execute on Quantum Inspire
    console.print(f"2. Submitting circuit ({args.shots} shots)...")
    execution = execute_circuit(
        circuit_or_circuits=qc,
        backend=backend,
        shots=args.shots,
        verbose=True,
    )

    counts = execution["counts"]
    console.print(f"\n[bold green]Execution completed in {execution['elapsed_seconds']}s[/bold green]")
    console.print(f"Raw Qiskit counts (q0-right): {counts}")

    # Step 4: Endianness & Probabilities
    # Qiskit returns q0 as the rightmost character; canonicalize reverses it so q0 is leftmost.
    canonical_counts = canonicalize_counts(counts, reverse_bits=True)
    probabilities = compute_probabilities(canonical_counts)

    console.print("\n[bold]Normalized Results (canonical q0-left):[/bold]")
    console.print(format_ascii_histogram(canonical_counts))

    p00 = probabilities.get("00", 0.0)
    p11 = probabilities.get("11", 0.0)
    entanglement_fidelity = p00 + p11
    console.print(f"\n[bold cyan]Combined |00> + |11> probability:[/bold cyan] {entanglement_fidelity * 100:.2f}%\n")


if __name__ == "__main__":
    main()
