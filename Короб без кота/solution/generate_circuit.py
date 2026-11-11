"""Правильная посылка: оптимизированная VaultKDF в circuit.json.

Это замена файла box-without-cat/generate_circuit.py. Запускать из каталога
box-without-cat, где импортируется пакет challenge.
"""

from __future__ import annotations

import json
from pathlib import Path

from challenge.circuit import TOTAL_QUBITS, parity_gadget

# У cx кубиты идут как (контрольный кубит, целевой кубит).
# Положительный фазовый коэффициент даёт T, отрицательный — T†,
# модуль числа — сколько раз повторить гейт.
CLIFFORD = [
    {"gate": "cx", "qubits": [4, 5]},
    {"gate": "x", "qubits": [9]},
    {"gate": "cx", "qubits": [4, 7]},
    {"gate": "cx", "qubits": [5, 8]},
    {"gate": "cx", "qubits": [0, 3]},
    {"gate": "cx", "qubits": [3, 6]},
    {"gate": "cx", "qubits": [1, 8]},
    {"gate": "x", "qubits": [2]},
]
PHASES = [
    ((0, 1, 4), 1),
    ((3, 6, 9), -1),
    ((1, 7), 1),
    ((0, 8, 9), -1),
]


def build() -> dict[str, object]:
    operations = list(CLIFFORD)
    for mask, coefficient in PHASES:
        operations.extend(
            {"gate": operation.gate, "qubits": list(operation.qubits)}
            for operation in parity_gadget(mask, coefficient)
        )
    return {"n_qubits": TOTAL_QUBITS, "operations": operations}


def main() -> None:
    path = Path("circuit.json")
    path.write_text(json.dumps(build(), indent=2) + "\n")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
