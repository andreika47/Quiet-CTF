"""Quantum Vault HTTP service."""

from __future__ import annotations

import base64
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from challenge.circuit import DATA_BITS, TOTAL_QUBITS, naive_program
from challenge.resources import budget, estimate_resources
from server.crypto import load_secret, open_flag, seal_flag
from server.executor import execute_with_qsim
from server.schema import Submission
from server.verifier import VerificationError, verify_submission

MAX_BODY_SIZE = 32_768


class BodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > MAX_BODY_SIZE
            except ValueError:
                return JSONResponse({"detail": "invalid content-length"}, status_code=400)
            if too_large:
                return JSONResponse({"detail": "request body is too large"}, status_code=413)
        return await call_next(request)


app = FastAPI(
    title="Quantum Vault",
    description="Submit an optimized affine phase-polynomial implementation of VaultKDF.",
    version="1.0.0",
)
app.add_middleware(BodySizeMiddleware)

_secret = load_secret()
_sealed_flag = seal_flag(os.environ.get("FLAG", "CTF{development_flag}"), _secret)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/challenge")
def challenge() -> dict[str, object]:
    return {
        "name": "Quantum Vault",
        "data_bits": DATA_BITS,
        "ancilla_bits": TOTAL_QUBITS - DATA_BITS,
        "bit_order": "little-endian",
        "allowed_gates": ["x", "cx", "t", "tdg"],
        "budget": budget(),
        "naive_resources": estimate_resources(naive_program()).as_dict(),
        "ciphertext": base64.b64encode(_sealed_flag.ciphertext).decode(),
        "nonce": base64.b64encode(_sealed_flag.nonce).decode(),
    }


@app.post("/solve")
def solve(submission: Submission) -> dict[str, object]:
    operations = submission.to_operations()
    try:
        report = verify_submission(operations)
        output = execute_with_qsim(operations, _secret)
        flag = open_flag(_sealed_flag, output)
    except VerificationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="candidate execution failed") from None
    return {
        "status": "accepted",
        "resources": report.as_dict(),
        "flag": flag,
    }
