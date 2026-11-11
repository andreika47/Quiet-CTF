"""Exact verifier for affine phase-polynomial circuit submissions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from challenge.circuit import (
    DATA_BITS,
    MODULUS,
    TOTAL_QUBITS,
    GateOp,
)
from challenge.resources import ResourceReport, estimate_resources
from server.reference import optimized_program


class VerificationError(ValueError):
    """A safe error that can be returned to a participant."""


@dataclass(frozen=True, slots=True)
class BasisAction:
    output: int
    phase: int


def evaluate_basis(operations: Iterable[GateOp], basis: int) -> BasisAction:
    """Evaluate a monomial circuit exactly, tracking powers of exp(i*pi/4)."""
    bits = [(basis >> index) & 1 for index in range(TOTAL_QUBITS)]
    phase = 0
    for operation in operations:
        gate = operation.gate
        if gate == "x":
            bits[operation.qubits[0]] ^= 1
        elif gate == "cx":
            control, target = operation.qubits
            bits[target] ^= bits[control]
        elif gate == "ccx":
            control_a, control_b, target = operation.qubits
            bits[target] ^= bits[control_a] & bits[control_b]
        elif gate in {"t", "tdg"}:
            phase += (1 if gate == "t" else -1) * bits[operation.qubits[0]]
        elif gate in {"add", "sub"}:
            data = sum(bits[index] << index for index in range(DATA_BITS))
            delta = operation.value or 0
            data = (data + delta if gate == "add" else data - delta) % MODULUS
            for index in range(DATA_BITS):
                bits[index] = (data >> index) & 1
        else:  # pragma: no cover - GateOp rejects this before verification.
            raise VerificationError("unsupported operation")
    output = sum(bit << index for index, bit in enumerate(bits))
    return BasisAction(output=output, phase=phase % 8)


@lru_cache(maxsize=1)
def reference_table() -> tuple[BasisAction, ...]:
    reference = optimized_program()
    return tuple(evaluate_basis(reference, basis) for basis in range(1 << TOTAL_QUBITS))


def verify_equivalence(operations: tuple[GateOp, ...]) -> None:
    expected = reference_table()
    global_phase: int | None = None
    for basis, reference_action in enumerate(expected):
        candidate_action = evaluate_basis(operations, basis)
        if candidate_action.output != reference_action.output:
            raise VerificationError("candidate is not equivalent to VaultKDF")
        difference = (candidate_action.phase - reference_action.phase) % 8
        if global_phase is None:
            global_phase = difference
        elif difference != global_phase:
            raise VerificationError("candidate is not equivalent to VaultKDF")


def verify_submission(operations: tuple[GateOp, ...]) -> ResourceReport:
    report = estimate_resources(operations)
    if not report.within_budget():
        raise VerificationError("resource budget exceeded")
    verify_equivalence(operations)
    return report
