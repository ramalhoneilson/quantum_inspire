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


def test_native_basis_gates_filters_rx():
    # Mock backend type with Tuna-17 gateset
    class MockBackendType:
        gateset = ["x", "y", "z", "h", "rx", "ry", "rz", "cz", "measure", "reset"]

    class MockBackend:
        def get_backend_type(self):
            return MockBackendType()

    gates = native_basis_gates(MockBackend())
    assert gates is not None
    # 'rx' must be excluded from the basis
    assert "rx" not in gates
    assert "cz" in gates
    assert "ry" in gates
    assert "rz" in gates
