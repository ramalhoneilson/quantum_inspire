"""Execution orchestrator, job serialization/recovery, and a polling loop."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Union

from qiskit import QuantumCircuit, transpile
from qiskit.providers.jobstatus import JobStatus

from qi_starter.backend import is_hardware, native_basis_gates


def transpile_for_backend(
    circuits: Union[QuantumCircuit, List[QuantumCircuit]],
    backend: Any,
    optimization_level: int = 3,
    seed_transpiler: int = 42,
) -> Union[QuantumCircuit, List[QuantumCircuit]]:
    """Transpile circuit(s) to the backend's native gateset.

    Uses `native_basis_gates` to restrict synthesis to gates the device supports.

    Args:
        circuits: A single QuantumCircuit or list of circuits.
        backend: The target QI backend.
        optimization_level: Transpilation optimization (default: 3).
        seed_transpiler: Random seed for deterministic transpilation.

    Returns:
        Transpiled circuit(s).
    """
    basis = native_basis_gates(backend)
    coupling_map = getattr(backend, "coupling_map", None)

    if basis:
        return transpile(
            circuits,
            coupling_map=coupling_map,
            basis_gates=basis,
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )
    return transpile(
        circuits,
        backend=backend,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )


def save_job_handle(job: Any, filepath: str) -> str:
    """Serialize a QIJob object to a QPY file on disk.

    Why this matters:
    QIJob in `qiskit_quantuminspire` assigns empty string to `job.job_id()`;
    the real job identifier is `job.batch_job_id`. Furthermore, the internal
    per-circuit job IDs needed to fetch results live on the in-memory object.
    `job.serialize(filepath)` writes a QPY file holding this state, allowing
    a separate script or post-restart process to resume polling without losing
    the job.

    Args:
        job: An active QIJob instance.
        filepath: Destination path (typically ending in `.qpy` or `.qijob.qpy`).

    Returns:
        str: Absolute path to the saved file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
    job.serialize(filepath)
    return os.path.abspath(filepath)


def load_job_handle(provider: Any, filepath: str) -> Any:
    """Deserialize a previously saved QPY file back into a pollable QIJob instance.

    Args:
        provider: An authenticated QIProvider instance.
        filepath: Path to the saved `.qpy` file.

    Returns:
        QIJob: Restored job instance ready to poll or retrieve results.
    """
    from qiskit_quantuminspire.qi_jobs import QIJob

    expanded = os.path.expanduser(filepath)
    if not os.path.exists(expanded):
        raise FileNotFoundError(f"Job handle file not found: {expanded}")
    return QIJob.deserialize(provider, expanded)


def extract_counts(result: Any, num_circuits: int) -> List[Dict[str, int]]:
    """Defensively extract measurement counts for each circuit in a result.

    Why this matters:
    Calling `result.get_counts()` without an index immediately raises an exception
    if even ONE circuit in a multi-circuit batch failed on the backend.
    Iterating with `result.get_counts(i)` isolates failures to individual circuits,
    preserving the results of all successfully executed circuits.

    Args:
        result: Qiskit Result object returned by `job.result()`.
        num_circuits: Number of circuits submitted in the batch.

    Returns:
        List of count dictionaries, one per circuit (empty dict for failed circuits).
    """
    counts_list: List[Dict[str, int]] = []
    for i in range(num_circuits):
        try:
            c = result.get_counts(i)
            counts_list.append(dict(c) if isinstance(c, dict) else {})
        except Exception:
            counts_list.append({})
    return counts_list


def poll_job(
    job: Any, timeout: int = 300, poll_interval: int = 3, verbose: bool = True
) -> Any:
    """Poll an active QIJob until it reaches completion or times out.

    Args:
        job: The QIJob to poll.
        timeout: Maximum seconds to wait before giving up.
        poll_interval: Seconds between status queries.
        verbose: Whether to print progress dots/status to stdout.

    Returns:
        The Qiskit Result object.

    Raises:
        TimeoutError: If the job does not complete within `timeout` seconds.
        RuntimeError: If the job encounters an unrecoverable status error.
    """
    deadline = time.time() + timeout
    batch_id = getattr(job, "batch_job_id", "unknown")

    if verbose:
        print(f"Polling job {batch_id} (timeout={timeout}s, interval={poll_interval}s)...")

    last_status = None
    while time.time() < deadline:
        status = job.status()
        if status != last_status and verbose:
            print(f"  Status: {status.name}")
            last_status = status

        if status == JobStatus.DONE:
            if verbose:
                print("  Job completed successfully.")
            return job.result()

        if status in (JobStatus.ERROR, JobStatus.CANCELLED):
            raise RuntimeError(f"Job {batch_id} terminated with error status: {status}")

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Job {batch_id} did not finish within {timeout} seconds. Current status: {last_status}"
    )


def execute_circuit(
    circuit_or_circuits: Union[QuantumCircuit, List[QuantumCircuit]],
    backend: Any,
    shots: int = 1024,
    armed: bool = False,
    transpile_circuit: bool = True,
    save_handle_path: Optional[str] = None,
    timeout: int = 300,
    poll_interval: int = 3,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Execute circuit(s) on Quantum Inspire with preflight validation and safeguards.

    Args:
        circuit_or_circuits: A single QuantumCircuit or list of circuits.
        backend: QI backend (e.g. `provider.get_backend("QX emulator")`).
        shots: Number of repetitions.
        armed: Guard flag; must be True to submit to real hardware QPUs.
        transpile_circuit: Whether to transpile with native basis gates first.
        save_handle_path: Optional path to save `.qpy` job handle for asynchronous recovery.
        timeout: Polling timeout in seconds.
        poll_interval: Polling interval in seconds.
        verbose: Print progress output.

    Returns:
        Dictionary containing:
            - batch_job_id: str, QI batch job ID
            - counts: list of count dictionaries (one per circuit)
            - shots: int
            - elapsed_seconds: float
            - result: Result object
            - handle_path: str or None
    """
    is_list = isinstance(circuit_or_circuits, list)
    circuits = circuit_or_circuits if is_list else [circuit_or_circuits]
    backend_name = getattr(backend, "name", str(backend))

    # Preflight Check 1: Hardware safety guard
    if is_hardware(backend_name) and not armed:
        raise PermissionError(
            f"Backend '{backend_name}' is physical quantum hardware.\n"
            "To prevent accidental quota consumption, you must pass armed=True "
            "(or the --armed CLI flag) to confirm submission."
        )

    # Preflight Check 2: Max shots
    max_shots = getattr(backend, "max_shots", None)
    if callable(max_shots):
        max_shots = max_shots()
    if max_shots and shots > int(max_shots):
        raise ValueError(
            f"Requested {shots} shots, but {backend_name} allows at most {max_shots} shots."
        )

    # Preflight Check 3: Max batch size
    backend_type = getattr(backend, "get_backend_type", lambda: None)()
    if backend_type:
        max_jobs = getattr(backend_type, "max_jobs_per_batch_job", None)
        if max_jobs and len(circuits) > int(max_jobs):
            raise ValueError(
                f"Batch contains {len(circuits)} circuits, but {backend_name} "
                f"allows at most {max_jobs} circuits per batch job. "
                "Use chunk_ranges() to divide into smaller batches."
            )

    # Transpilation
    if transpile_circuit:
        if verbose:
            print(f"Transpiling {len(circuits)} circuit(s) for {backend_name}...")
        circuits_to_run = transpile_for_backend(circuits, backend)
    else:
        circuits_to_run = circuits

    # Submission
    start_time = time.time()
    payload = circuits_to_run if is_list else circuits_to_run[0]
    if verbose:
        print(f"Submitting {len(circuits)} circuit(s) to '{backend_name}' ({shots} shots)...")
    job = backend.run(payload, shots=shots)

    batch_id = getattr(job, "batch_job_id", "")
    if verbose:
        print(f"Submitted. Provider batch job ID: {batch_id}")

    # Optional handle serialization
    saved_path = None
    if save_handle_path:
        saved_path = save_job_handle(job, save_handle_path)
        if verbose:
            print(f"Saved job handle to: {saved_path}")

    # Polling
    result = poll_job(job, timeout=timeout, poll_interval=poll_interval, verbose=verbose)
    elapsed = round(time.time() - start_time, 2)

    # Count extraction
    counts_list = extract_counts(result, len(circuits))

    return {
        "batch_job_id": batch_id,
        "backend_name": backend_name,
        "shots": shots,
        "elapsed_seconds": elapsed,
        "counts": counts_list if is_list else counts_list[0],
        "result": result,
        "handle_path": saved_path,
    }
