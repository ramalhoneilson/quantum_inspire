"""Quantum Inspire Starter: beginner-friendly utilities and production infrastructure
for executing quantum circuits on Quantum Inspire (emulators and superconducting QPUs).
"""

from qi_starter.auth import check_auth_status, get_provider
from qi_starter.backend import (
    describe_backends,
    get_backend_info,
    is_hardware,
    native_basis_gates,
    chunk_ranges,
)
from qi_starter.circuits import (
    create_bell_circuit,
    create_ghz_circuit,
    create_grover_circuit,
)
from qi_starter.runner import (
    execute_circuit,
    poll_job,
    save_job_handle,
    load_job_handle,
    extract_counts,
)
from qi_starter.results import (
    canonicalize_counts,
    compute_probabilities,
    wilson_interval,
    format_ascii_histogram,
    hellinger_distance,
)

__version__ = "0.1.0"
__all__ = [
    "check_auth_status",
    "get_provider",
    "describe_backends",
    "get_backend_info",
    "is_hardware",
    "native_basis_gates",
    "chunk_ranges",
    "create_bell_circuit",
    "create_ghz_circuit",
    "create_grover_circuit",
    "execute_circuit",
    "poll_job",
    "save_job_handle",
    "load_job_handle",
    "extract_counts",
    "canonicalize_counts",
    "compute_probabilities",
    "wilson_interval",
    "format_ascii_histogram",
    "hellinger_distance",
]
