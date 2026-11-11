"""Cirq conversion and qsim execution."""

from __future__ import annotations

import cirq
import qsimcirq

from challenge.circuit import DATA_BITS, TOTAL_QUBITS, GateOp


def to_cirq(operations: tuple[GateOp, ...]) -> cirq.Circuit:
    qubits = cirq.LineQubit.range(TOTAL_QUBITS)
    circuit = cirq.Circuit()
    for operation in operations:
        if operation.gate == "x":
            circuit.append(cirq.X(qubits[operation.qubits[0]]))
        elif operation.gate == "cx":
            control, target = operation.qubits
            circuit.append(cirq.CNOT(qubits[control], qubits[target]))
        elif operation.gate == "t":
            circuit.append(cirq.T(qubits[operation.qubits[0]]))
        elif operation.gate == "tdg":
            circuit.append((cirq.T**-1)(qubits[operation.qubits[0]]))
        else:
            raise ValueError("submission contains a non-executable gate")
    return circuit


def execute_with_qsim(operations: tuple[GateOp, ...], secret: int) -> int:
    """Run the accepted circuit on a hidden computational-basis input."""
    if secret < 0 or secret >= 1 << DATA_BITS:
        raise ValueError("secret does not fit the data register")
    qubits = cirq.LineQubit.range(TOTAL_QUBITS)
    preparation = [cirq.X(qubits[index]) for index in range(DATA_BITS) if secret >> index & 1]
    circuit = cirq.Circuit(preparation)
    circuit += to_cirq(operations)
    circuit.append(cirq.measure(*qubits, key="result"))

    simulator = qsimcirq.QSimSimulator(
        qsim_options=qsimcirq.QSimOptions(cpu_threads=1, verbosity=0)
    )
    sample = simulator.run(circuit, repetitions=1).measurements["result"][0]
    if any(sample[DATA_BITS:]):
        raise ValueError("candidate did not restore its clean анцилла")
    return sum(int(sample[index]) << index for index in range(DATA_BITS))
