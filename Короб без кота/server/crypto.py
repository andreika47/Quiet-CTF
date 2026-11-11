"""Flag sealing tied to the hidden VaultKDF output."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from challenge.circuit import DATA_BITS
from server.reference import optimized_program
from server.verifier import evaluate_basis

AAD = b"quantum-vault-ctf-v1"


@dataclass(frozen=True, slots=True)
class SealedFlag:
    nonce: bytes
    ciphertext: bytes


def load_secret() -> int:
    value = int(os.environ.get("VAULT_SECRET", "0x2a5"), 0)
    if value < 0 or value >= 1 << DATA_BITS:
        raise RuntimeError(f"VAULT_SECRET must be a {DATA_BITS}-bit integer")
    return value


def _key(output: int) -> bytes:
    material = output.to_bytes(2, "little") + AAD
    return hashlib.sha256(material).digest()


def seal_flag(flag: str, secret: int) -> SealedFlag:
    output = evaluate_basis(optimized_program(), secret).output & ((1 << DATA_BITS) - 1)
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key(output)).encrypt(nonce, flag.encode(), AAD)
    return SealedFlag(nonce=nonce, ciphertext=ciphertext)


def open_flag(sealed: SealedFlag, output: int) -> str:
    plaintext = AESGCM(_key(output)).decrypt(sealed.nonce, sealed.ciphertext, AAD)
    return plaintext.decode()
