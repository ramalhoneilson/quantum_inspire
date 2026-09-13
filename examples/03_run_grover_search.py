#!/usr/bin/env python3
"""Example 3: Run 2-qubit Grover Search on Quantum Inspire.

Demonstrates:
  - Running a complete quantum algorithm (Grover search)
  - Comparing empirical counts against ideal theoretical prediction
  - Calculating 95% Wilson score confidence interval for success probability
  - Computing Hellinger distance against the ideal distribution

Usage:
    python examples/03_run_grover_search.py [--marked 10] [--shots 1024]
"""

from __future__ import annotations

import argparse
from rich.console import Console

from qi_starter.auth import get_provider
from qi_starter.circuits import create_grover_circuit
from qi_starter.results import (
    canonicalize_counts,
    compute_probabilities,
    format_ascii_histogram,
    hellinger_distance,
    wilson_interval,
)
from qi_starter.runner import execute_circuit


def main():
    parser = argparse.ArgumentParser(description="Run 2-qubit Grover search on Quantum Inspire.")
    parser.add_argument("--marked", default="10", choices=["00", "01", "10", "11"],
                        help="Marked target state in q0-left order (default: '10')")
    parser.add_argument("--backend", default="QX emulator",
                        help="Backend to execute on (default: 'QX emulator')")
    parser.add_argument("--shots", type=int, default=1024,
                        help="Number of shots (default: 1024)")
    args = parser.parse_args()

    console = Console()
    console.print(f"\n[bold cyan]=== 2-Qubit Grover Search (Target: |{args.marked}>) on '{args.backend}' ===[/bold cyan]\n")

    # Step 1: Create algorithm circuit
    console.print(f"1. Building Grover search circuit with oracle marked for |{args.marked}>...")
    qc = create_grover_circuit(marked_state=args.marked)
    console.print(f"[dim]{qc.draw(output='text')}[/dim]\n")

    # Step 2: Connect and submit
    provider = get_provider()
    backend = provider.get_backend(args.backend)

    console.print(f"2. Executing algorithm ({args.shots} shots)...")
    execution = execute_circuit(
        circuit_or_circuits=qc,
        backend=backend,
        shots=args.shots,
        verbose=True,
    )

    counts = execution["counts"]
    # Reversing bits translates from Qiskit's q0-right to canonical q0-left
    canonical_counts = canonicalize_counts(counts, reverse_bits=True)
    probabilities = compute_probabilities(canonical_counts)

    console.print("\n[bold]Execution Results:[/bold]")
    console.print(format_ascii_histogram(canonical_counts))

    # Step 3: Statistical Evaluation
    successes = canonical_counts.get(args.marked, 0)
    total_shots = execution["shots"]
    success_rate = probabilities.get(args.marked, 0.0)
    lower, upper = wilson_interval(successes, total_shots, confidence=0.95)

    ideal_dist = {args.marked: 1.0}
    h_dist = hellinger_distance(probabilities, ideal_dist)

    console.print(f"\n[bold]Target State Analysis (|{args.marked}>):[/bold]")
    console.print(f"  Successes: [green]{successes}/{total_shots}[/green]")
    console.print(f"  Success Probability: [bold green]{success_rate * 100:.2f}%[/bold green]")
    console.print(f"  95% Wilson Confidence Interval: [{lower * 100:.2f}%, {upper * 100:.2f}%]")
    console.print(f"  Hellinger Distance to Exact Ideal: [cyan]{h_dist:.4f}[/cyan] (0.0 = perfect match)\n")


if __name__ == "__main__":
    main()
