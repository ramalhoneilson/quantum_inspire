"""Unit tests for circuit generation utilities."""

import pytest
from qi_starter.circuits import (
    create_bell_circuit,
    create_ghz_circuit,
    create_grover_circuit,
)


def test_create_bell_circuit():
    qc = create_bell_circuit()
    assert qc.num_qubits == 2
    assert qc.num_clbits == 2
    ops = qc.count_ops()
    assert ops.get("h") == 1
    assert ops.get("cx") == 1
    assert ops.get("measure") == 2


def test_create_ghz_circuit():
    qc3 = create_ghz_circuit(num_qubits=3)
    assert qc3.num_qubits == 3
    assert qc3.num_clbits == 3
    ops = qc3.count_ops()
    assert ops.get("h") == 1
    assert ops.get("cx") == 2

    with pytest.raises(ValueError, match="at least 2 qubits"):
        create_ghz_circuit(num_qubits=1)


def test_create_grover_circuit_valid():
    for marked in ("00", "01", "10", "11"):
        qc = create_grover_circuit(marked)
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert "measure" in qc.count_ops()


def test_create_grover_circuit_invalid():
    with pytest.raises(ValueError, match="2-character binary string"):
        create_grover_circuit("101")

    with pytest.raises(ValueError, match="2-character binary string"):
        create_grover_circuit("ab")
