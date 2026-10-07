"""Backend discovery, capability extraction, and hardware-specific workarounds."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


SIMULATOR_HINTS = ("emulator", "simulator", "qx")

# Mapping from Quantum Inspire gateset names to Qiskit standard gate names
_QI_GATESET_TO_QISKIT: Dict[str, str] = {
    "i": "id",
    "x": "x",
    "y": "y",
    "z": "z",
    "h": "h",
    "s": "s",
    "t": "t",
    "sdag": "sdg",
    "tdag": "tdg",
    "rx": "rx",
    "ry": "ry",
    "rz": "rz",
    "cz": "cz",
    "cnot": "cx",
    "swap": "swap",
    "toffoli": "ccx",
    "measure": "measure",
    "reset": "reset",
}

# Precaution for Tuna-17: it advertises 'rx', but we observed circuits transpiled
# with 'rx' behaving as if the rotation angle were negated. The root cause has not
# been confirmed. 'ry' and 'rz' together span all single-qubit rotations, so
# excluding 'rx' from the transpiler basis loses nothing; Qiskit synthesizes with
# ry/rz instead. The exclusion is applied to every backend (it costs nothing on
# emulators).
_QI_UNRELIABLE_GATES: Set[str] = {"rx"}


def is_hardware(name_or_backend: Any) -> bool:
    """Check whether a backend is a real quantum processing unit (QPU) or an emulator.

    Args:
        name_or_backend: Either the string name of the backend or a backend object.

    Returns:
        bool: True if physical hardware, False if an emulator/simulator.
    """
    name = (
        name_or_backend
        if isinstance(name_or_backend, str)
        else getattr(name_or_backend, "name", str(name_or_backend))
    )
    lowered = name.lower()
    return not any(hint in lowered for hint in SIMULATOR_HINTS)


def native_basis_gates(backend: Any) -> Optional[List[str]]:
    """Determine the true physical native basis gates for a Quantum Inspire backend.

    By default, `qiskit_quantuminspire` advertises a static target basis that
    includes gates not physically implemented by the chip (e.g. CX or SWAP on Tuna-17,
    which natively implements CZ). Furthermore, `rx` is excluded as a precaution
    (we observed it behaving as if the angle were negated on Tuna-17; the root
    cause is unconfirmed). The exclusion applies to all backends, including
    emulators, where it costs nothing because `ry` and `rz` span all single-qubit
    rotations.

    Args:
        backend: A Qiskit Backend object from QIProvider.

    Returns:
        List of Qiskit gate names (e.g. ['cz', 'h', 'measure', 'reset', 'ry', 'rz', 'x', ...])
        or None if device gateset is not retrievable.
    """
    backend_type = getattr(backend, "get_backend_type", lambda: None)()
    if not backend_type:
        # Fall back to target operation names if available
        target = getattr(backend, "target", None)
        if target is not None and hasattr(target, "operation_names"):
            return sorted(list(target.operation_names))
        return None

    gateset = getattr(backend_type, "gateset", None)
    if not gateset:
        return None

    mapped = {
        _QI_GATESET_TO_QISKIT[name.lower()]
        for name in gateset
        if name.lower() in _QI_GATESET_TO_QISKIT
    }
    # Exclude gates we treat as unreliable (currently only 'rx')
    return sorted(mapped - _QI_UNRELIABLE_GATES)


def chunk_ranges(count: int, limit: int) -> List[Tuple[int, int]]:
    """Partition `count` items into contiguous slices of at most `limit` items each.

    Quantum Inspire limits the number of circuits that can be submitted in a single
    batch job (`max_jobs_per_batch_job`). This helper divides large batches into
    safe chunks that can be submitted sequentially.

    Args:
        count: Total number of circuits.
        limit: Maximum circuits permitted per batch job (0 or less means unlimited).

    Returns:
        List of (start, end) index tuples.
    """
    if count <= 0:
        return []
    if limit <= 0 or count <= limit:
        return [(0, count)]
    return [(i, min(i + limit, count)) for i in range(0, count, limit)]


def get_backend_info(backend: Any) -> Dict[str, Any]:
    """Extract key properties and operational limits from a QI backend.

    Args:
        backend: A Qiskit Backend object from QIProvider.

    Returns:
        Dictionary of backend properties including qubit count, limits, and status.
    """
    backend_type = getattr(backend, "get_backend_type", lambda: None)()
    name = getattr(backend, "name", str(backend))

    max_shots = getattr(backend, "max_shots", None)
    if callable(max_shots):
        max_shots = max_shots()

    max_jobs = getattr(backend_type, "max_jobs_per_batch_job", None) if backend_type else None
    queue_limit = getattr(backend_type, "batchjobs_per_queue_limit", None) if backend_type else None

    status_val = getattr(backend, "status", None)
    if callable(status_val):
        status_val = status_val()
    status_str = getattr(status_val, "value", str(status_val)) if status_val else "unknown"

    return {
        "name": name,
        "is_hardware": is_hardware(name),
        "num_qubits": getattr(backend, "num_qubits", None),
        "max_shots": max_shots,
        "max_jobs_per_batch_job": int(max_jobs) if max_jobs is not None else None,
        "queue_limit": int(queue_limit) if queue_limit is not None else None,
        "status": status_str,
        "native_basis_gates": native_basis_gates(backend),
    }


def describe_backends(provider: Any) -> List[Dict[str, Any]]:
    """List and describe all backends accessible with the current QI account.

    Args:
        provider: An authenticated QIProvider instance.

    Returns:
        A list of backend description dictionaries.
    """
    rows = []
    for backend in provider.backends():
        info = get_backend_info(backend)
        rows.append(info)
    return rows
