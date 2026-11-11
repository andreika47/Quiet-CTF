"""Private canonical form used by the remote checker."""

from __future__ import annotations

from challenge.circuit import GateOp, parity_gadget


def optimized_program() -> tuple[GateOp, ...]:
    operations = [
        GateOp("cx", (4, 5)),
        GateOp("x", (9,)),
        GateOp("cx", (4, 7)),
        GateOp("cx", (5, 8)),
        GateOp("cx", (0, 3)),
        GateOp("cx", (3, 6)),
        GateOp("cx", (1, 8)),
        GateOp("x", (2,)),
    ]
    for mask, coefficient in (
        ((0, 1, 4), 1),
        ((3, 6, 9), -1),
        ((1, 7), 1),
        ((0, 8, 9), -1),
    ):
        operations.extend(parity_gadget(mask, coefficient))
    return tuple(operations)
