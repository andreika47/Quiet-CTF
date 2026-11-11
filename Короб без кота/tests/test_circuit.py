from challenge.bloqs import VaultKDF
from challenge.circuit import TOTAL_QUBITS, naive_program
from challenge.resources import estimate_resources
from server.reference import optimized_program
from server.verifier import evaluate_basis, verify_submission


def test_qualtran_decomposition_contains_every_instruction() -> None:
    composite = VaultKDF().decompose_bloq()
    assert len(composite.bloq_instances) == len(naive_program())


def test_naive_and_optimized_programs_are_exactly_equivalent() -> None:
    naive = naive_program()
    optimized = optimized_program()
    for basis in range(1 << TOTAL_QUBITS):
        assert evaluate_basis(naive, basis) == evaluate_basis(optimized, basis)


def test_only_optimized_program_fits_budget() -> None:
    naive_report = estimate_resources(naive_program())
    optimized_report = verify_submission(optimized_program())

    assert not naive_report.within_budget()
    assert naive_report.t_count > 700
    assert optimized_report.within_budget()
    assert optimized_report.t_count == 4
