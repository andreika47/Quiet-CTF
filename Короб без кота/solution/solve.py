"""Organizer solution: derive and submit the canonical phase polynomial."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


def parity(mask: tuple[int, ...], gate: str) -> list[dict[str, object]]:
    pivot = mask[-1]
    controls = mask[:-1]
    result = [{"gate": "cx", "qubits": [control, pivot]} for control in controls]
    result.append({"gate": gate, "qubits": [pivot]})
    result.extend({"gate": "cx", "qubits": [control, pivot]} for control in reversed(controls))
    return result


def solution() -> dict[str, object]:
    operations: list[dict[str, object]] = [
        {"gate": "cx", "qubits": [4, 5]},
        {"gate": "x", "qubits": [9]},
        {"gate": "cx", "qubits": [4, 7]},
        {"gate": "cx", "qubits": [5, 8]},
        {"gate": "cx", "qubits": [0, 3]},
        {"gate": "cx", "qubits": [3, 6]},
        {"gate": "cx", "qubits": [1, 8]},
        {"gate": "x", "qubits": [2]},
    ]
    for mask, gate in (
        ((0, 1, 4), "t"),
        ((3, 6, 9), "tdg"),
        ((1, 7), "t"),
        ((0, 8, 9), "tdg"),
    ):
        operations.extend(parity(mask, gate))
    return {"n_qubits": 12, "operations": operations}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Submit to this service URL")
    parser.add_argument("--output", type=Path, default=Path("solution.json"))
    args = parser.parse_args()

    payload = json.dumps(solution(), indent=2).encode()
    args.output.write_bytes(payload)
    print(f"Wrote {args.output}")
    if args.url:
        request = urllib.request.Request(
            f"{args.url.rstrip('/')}/solve",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            print(response.read().decode())


if __name__ == "__main__":
    main()
