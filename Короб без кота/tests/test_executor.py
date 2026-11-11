from challenge.circuit import DATA_BITS
from server.executor import execute_with_qsim
from server.reference import optimized_program
from server.verifier import evaluate_basis


def test_qsim_matches_exact_interpreter() -> None:
    operations = optimized_program()
    for secret in (0, 1, 0x155, 0x2A5, (1 << DATA_BITS) - 1):
        expected = evaluate_basis(operations, secret).output & ((1 << DATA_BITS) - 1)
        assert execute_with_qsim(operations, secret) == expected
