"""Strict, non-executable submission format."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from challenge.circuit import GateOp, SUBMISSION_GATES, TOTAL_QUBITS
from challenge.resources import MAX_OPERATIONS


class OperationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate: Literal["x", "cx", "t", "tdg"]
    qubits: list[int] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_qubits(self) -> "OperationInput":
        expected = 2 if self.gate == "cx" else 1
        if len(self.qubits) != expected:
            raise ValueError(f"{self.gate} expects {expected} qubit(s)")
        if len(set(self.qubits)) != len(self.qubits):
            raise ValueError("gate qubits must be distinct")
        if any(index < 0 or index >= TOTAL_QUBITS for index in self.qubits):
            raise ValueError(f"qubit indices must be in [0, {TOTAL_QUBITS - 1}]")
        return self

    def to_gate_op(self) -> GateOp:
        if self.gate not in SUBMISSION_GATES:  # Defensive check if the schema changes.
            raise ValueError("gate is not allowed in submissions")
        return GateOp(self.gate, tuple(self.qubits))


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    n_qubits: Literal[12]
    operations: list[OperationInput] = Field(min_length=1, max_length=MAX_OPERATIONS)

    def to_operations(self) -> tuple[GateOp, ...]:
        return tuple(operation.to_gate_op() for operation in self.operations)
