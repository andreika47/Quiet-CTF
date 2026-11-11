from pathlib import Path

import cirq
import numpy as np

from challenge import bits_to_bytes, conjugate_ops, one_qubit_circuit, public_ops


DUMP_PATH = Path(__file__).resolve().with_name("challenge.txt")
BASES = ("Z", "X", "Y")


def parse_dump(text):
    nonce = None
    key_len = None
    rows = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Nonce (hex) = "):
            nonce = bytes.fromhex(line.split("=", 1)[1].strip())
        elif line.startswith("Длина сообщения (бит) = "):
            key_len = int(line.split("=", 1)[1].strip())
        elif line and line[0].isdigit() and "pad_x=" in line:
            head, rest = line.split(":", 1)
            index = int(head)
            fields = {}
            for token in rest.split():
                name, value = token.split("=", 1)
                fields[name] = value
            amp0 = _amp(fields["amp0"])
            amp1 = _amp(fields["amp1"])
            rows[index] = (
                int(fields["pad_x"]),
                int(fields["pad_z"]),
                np.array([amp0, amp1], dtype=np.complex64),
            )
    if nonce is None or key_len is None or len(rows) != key_len:
        raise ValueError("dump is missing nonce, length, or qubit lines")
    if sorted(rows) != list(range(key_len)):
        raise ValueError("qubit indices are not 0..n-1")
    return nonce, [rows[i] for i in range(key_len)]


def _amp(text):
    real, imag = text.split(",")
    return complex(float(real), float(imag))


def reference_states(sim):
    q = cirq.LineQubit(0)
    table = []
    for basis in BASES:
        for bit in (0, 1):
            state = sim.simulate(
                one_qubit_circuit(q, conjugate_ops(q, bit, basis))
            ).final_state_vector
            table.append((bit, state))
    return table


def undo_public(state, pad_x, pad_z, index, nonce, sim):
    q = cirq.LineQubit(0)
    forward = public_ops(q, pad_x, pad_z, index, nonce)
    backward = [cirq.inverse(op) for op in reversed(forward)]
    restored = sim.simulate(
        one_qubit_circuit(q, backward), initial_state=state
    ).final_state_vector
    restored = np.asarray(restored, dtype=np.complex64)
    return restored / np.linalg.norm(restored)


def classify(state, table):
    scores = [abs(np.vdot(ref, state)) ** 2 for _, ref in table]
    best = int(np.argmax(scores))
    if scores[best] < 0.98:
        raise ValueError(f"no six-state match (best fidelity {scores[best]:.4f})")
    return table[best][0]


def recover(text):
    nonce, qubits = parse_dump(text)
    sim = cirq.Simulator()
    table = reference_states(sim)
    bits = []
    for index, (pad_x, pad_z, state) in enumerate(qubits):
        restored = undo_public(state, pad_x, pad_z, index, nonce, sim)
        bits.append(classify(restored, table))
    return bits_to_bytes(bits)


def main():
    plain = recover(DUMP_PATH.read_text(encoding="utf-8"))
    print(f"qubits={len(plain) * 8}")
    print(plain.decode())


if __name__ == "__main__":
    main()
