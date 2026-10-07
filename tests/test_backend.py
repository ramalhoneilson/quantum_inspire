"""Unit tests for backend discovery and batch chunking."""

from qi_starter.backend import chunk_ranges, is_hardware, native_basis_gates


def test_chunk_ranges():
    # Exactly fits in one chunk
    assert chunk_ranges(5, 10) == [(0, 5)]

    # Multiple chunks
    assert chunk_ranges(12, 5) == [(0, 5), (5, 10), (10, 12)]

    # Empty
    assert chunk_ranges(0, 5) == []

    # Limit <= 0 means unlimited
    assert chunk_ranges(10, 0) == [(0, 10)]


def test_is_hardware():
    assert not is_hardware("QX emulator")
    assert not is_hardware("Ry emulator")
    assert not is_hardware("Simulator")
    assert is_hardware("Tuna-5")
    assert is_hardware("Tuna-17")
    assert is_hardware("Spin-2")


def test_native_basis_gates_maps_gateset():
    class MockBackendType:
        gateset = ["x", "h", "rx", "ry", "rz", "cz", "cnot", "sdag", "foo", "measure"]

    class MockBackend:
        def get_backend_type(self):
            return MockBackendType()

    gates = native_basis_gates(MockBackend())
    assert gates == sorted(gates)
    for name in ("rx", "ry", "rz", "cz", "cx", "sdg", "h", "x", "measure"):
        assert name in gates
    # Unknown names are ignored; QI names are translated
    assert "foo" not in gates
    assert "cnot" not in gates
    assert "sdag" not in gates
