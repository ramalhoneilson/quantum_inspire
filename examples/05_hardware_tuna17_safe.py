#!/usr/bin/env python3
"""Example 5: Safe execution on real quantum hardware (Tuna-17) with the Quanifi gate fix.

Demonstrates:
  - Safety guards: requires `--armed` to spend real QPU quota
  - Hardware basis gate inspection (excluding Tuna-17's faulty `rx` gate)
  - Transpiling into real physical gates ({cz, ry, rz, h, x, y, z})
  - Preflight analysis without spending compute time

Usage:
    # Dry run (preflight only, safe, spends zero quota):
    python examples/05_hardware_tuna17_safe.py

    # Real hardware execution (requires confirmation):
    python examples/05_hardware_tuna17_safe.py --armed --shots 1024
"""

from __future__ import annotations

import argparse
import sys
from rich.console import Console

from qi_starter.auth import get_provider
from qi_starter.backend import get_backend_info, is_hardware, native_basis_gates
from qi_starter.circuits import create_grover_circuit
from qi_starter.results import canonicalize_counts, format_ascii_histogram, wilson_interval
from qi_starter.runner import execute_circuit, transpile_for_backend


def main():
    parser = argparse.ArgumentParser(description="Safely execute on Quantum Inspire physical hardware.")
    parser.add_argument("--backend", default="Tuna-17", help="Target hardware QPU (default: Tuna-17)")
    parser.add_argument("--shots", type=int, default=1024, help="Measurement shots (default: 1024)")
    parser.add_argument("--armed", action="store_true", help="Arm submission to spend real hardware quota")
    args = parser.parse_args()

    console = Console()
    console.print(f"\n[bold cyan]=== Physical Hardware Execution: {args.backend} ===[/bold cyan]\n")

    provider = get_provider()
    backend = provider.get_backend(args.backend)
    info = get_backend_info(backend)

    console.print(f"Target Backend: [bold]{args.backend}[/bold]")
    console.print(f"Physical Qubits: {info['num_qubits']}")
    console.print(f"Device Status: {info['status']}")

    # 1. Native Basis Gates & The Tuna-17 'rx' Defect Explanation
    basis = native_basis_gates(backend)
    console.print(f"\n[bold]Resolved Physical Basis Gates:[/bold] [green]{basis}[/green]")
    console.print(
        "[dim]Note: 'rx' is deliberately omitted because Tuna-17 hardware inverts the rotation "
        "angle on rx. Excluding rx forces the transpiler to synthesize using ry and rz, "
        "which execute correctly on the chip.[/dim]\n"
    )

    # 2. Transpilation Preflight
    qc = create_grover_circuit(marked_state="10")
    console.print("Transpiling 2-qubit Grover circuit to match hardware topology and gateset...")
    transpiled_qc = transpile_for_backend(qc, backend, optimization_level=3)

    ops = transpiled_qc.count_ops()
    two_q_gates = ops.get("cz", 0) + ops.get("cx", 0)
    console.print(f"Transpiled circuit depth: [yellow]{transpiled_qc.depth()}[/yellow]")
    console.print(f"Operations: {dict(ops)}")
    console.print(f"Two-qubit gate count: [yellow]{two_q_gates}[/yellow]\n")

    # 3. Hardware Guard Check
    if is_hardware(args.backend) and not args.armed:
        console.print("[bold yellow]⚠️  PREFLIGHT ONLY: Hardware safety guard active![/bold yellow]")
        console.print("To submit this job to the physical QPU and spend quota, re-run with:")
        console.print(f"    [bold green]python examples/05_hardware_tuna17_safe.py --backend {args.backend} --armed[/bold green]\n")
        return

    # 4. Actual Hardware Execution
    console.print(f"[bold red]⚡ ARMED: Submitting job to physical hardware {args.backend}...[/bold red]")
    execution = execute_circuit(
        circuit_or_circuits=transpiled_qc,
        backend=backend,
        shots=args.shots,
        armed=args.armed,
        transpile_circuit=False,  # already transpiled above
        verbose=True,
    )

    counts = execution["counts"]
    console.print(f"\n[bold green]Hardware run finished in {execution['elapsed_seconds']}s. Job ID: {execution['batch_job_id']}[/bold green]")

    canonical = canonicalize_counts(counts, reverse_bits=True)
    console.print("\n[bold]Measured Physical Hardware Counts (q0-left):[/bold]")
    console.print(format_ascii_histogram(canonical))

    # Evaluate target fidelity on noisy hardware
    successes = canonical.get("10", 0)
    total_shots = args.shots
    success_rate = successes / total_shots if total_shots else 0.0
    lower, upper = wilson_interval(successes, total_shots, confidence=0.95)
    console.print(f"\nTarget |10> Success: {successes}/{total_shots} ({success_rate * 100:.2f}%)")
    console.print(f"95% Confidence Interval: [{lower * 100:.2f}%, {upper * 100:.2f}%]\n")


if __name__ == "__main__":
    main()
