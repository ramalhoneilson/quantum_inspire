"""Standard benchmark and educational quantum circuits for Quantum Inspire."""

from __future__ import annotations

from qiskit import QuantumCircuit


def create_bell_circuit() -> QuantumCircuit:
    """Create a 2-qubit Bell state: (|00> + |11>) / sqrt(2).

    Returns:
        QuantumCircuit: 2 qubits, 2 classical bits with Bell pair and measurement.
    """
    qc = QuantumCircuit(2, 2, name="bell_state")
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def create_ghz_circuit(num_qubits: int = 3) -> QuantumCircuit:
    """Create an N-qubit GHZ state: (|00...0> + |11...1>) / sqrt(2).

    Args:
        num_qubits: Number of entangled qubits (minimum 2).

    Returns:
        QuantumCircuit: N qubits entangled with measurement.
    """
    if num_qubits < 2:
        raise ValueError(f"GHZ circuit requires at least 2 qubits, got {num_qubits}")

    qc = QuantumCircuit(num_qubits, num_qubits, name=f"ghz_{num_qubits}q")
    qc.h(0)
    for i in range(num_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure(range(num_qubits), range(num_qubits))
    return qc


def create_grover_circuit(marked_state: str = "10") -> QuantumCircuit:
    """Create a 2-qubit, 1-iteration Grover search circuit for a marked state.

    This is the exact Grover algorithm used in Quanifi's hardware evaluation.
    For 2 qubits and 1 marked state, Grover's algorithm has a theoretical success
    probability of exactly 1.0 (100%) on an ideal noiseless simulator.
    Any departure from 100% when run on real hardware (such as Tuna-17)
    directly measures physical device error and noise.

    Note on bit order:
    `marked_state` is specified in standard reading order (q0-left). For example,
    with marked_state="10", qubit 0 is |1> and qubit 1 is |0>.

    Args:
        marked_state: 2-bit binary string to search for ("00", "01", "10", or "11").

    Returns:
        QuantumCircuit: 2-qubit Grover circuit with oracle, diffuser, and measurements.
    """
    if len(marked_state) != 2 or not all(c in "01" for c in marked_state):
        raise ValueError(
            f"marked_state must be a 2-character binary string ('00','01','10','11'), got '{marked_state}'"
        )

    qc = QuantumCircuit(2, 2, name=f"grover_{marked_state}")

    # Step 1: Initial superposition |++>
    qc.h(0)
    qc.h(1)

    # Step 2: Phase Oracle (flips phase of |marked_state>)
    # Bit 0 is q0, Bit 1 is q1
    if marked_state[0] == "0":
        qc.x(0)
    if marked_state[1] == "0":
        qc.x(1)

    # Controlled-Z between q0 and q1
    qc.h(1)
    qc.cx(0, 1)
    qc.h(1)

    if marked_state[0] == "0":
        qc.x(0)
    if marked_state[1] == "0":
        qc.x(1)

    # Step 3: Grover Diffuser (inversion about the mean)
    qc.h([0, 1])
    qc.x([0, 1])

    qc.h(1)
    qc.cx(0, 1)
    qc.h(1)

    qc.x([0, 1])
    qc.h([0, 1])

    # Step 4: Measurement
    qc.measure([0, 1], [0, 1])
    return qc
