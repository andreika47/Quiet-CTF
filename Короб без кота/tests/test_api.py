from fastapi.testclient import TestClient

from server.app import app
from server.reference import optimized_program

client = TestClient(app)


def payload(operations) -> dict[str, object]:
    return {
        "n_qubits": 12,
        "operations": [
            {"gate": operation.gate, "qubits": list(operation.qubits)}
            for operation in operations
        ],
    }


def test_challenge_metadata() -> None:
    response = client.get("/challenge")
    assert response.status_code == 200
    body = response.json()
    assert body["budget"]["t_count"] == 4
    assert body["naive_resources"]["t_count"] > body["budget"]["t_count"]


def test_reference_solution_returns_flag() -> None:
    response = client.post("/solve", json=payload(optimized_program()))
    assert response.status_code == 200
    assert response.json()["flag"].startswith("CTF{")


def test_missing_phase_gadget_is_rejected() -> None:
    operations = tuple(
        operation for operation in optimized_program() if operation.gate not in {"t", "tdg"}
    )
    response = client.post("/solve", json=payload(operations))
    assert response.status_code == 400
    assert response.json()["detail"] == "candidate is not equivalent to VaultKDF"


def test_invalid_gate_and_qubit_are_rejected_by_schema() -> None:
    invalid = {"n_qubits": 12, "operations": [{"gate": "h", "qubits": [99]}]}
    assert client.post("/solve", json=invalid).status_code == 422
