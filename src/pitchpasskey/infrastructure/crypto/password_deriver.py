from __future__ import annotations

import hashlib
import hmac
import string

from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.domain.ports import PasswordDerivationPort


class PasswordDeriver(PasswordDerivationPort):
    """Cross-machine deterministic password derivation from MIDI notes only."""

    _VERSION = b"PitchPassKey/password/v2"
    # This public, fixed salt is for domain separation—not a secret.
    # It intentionally stays constant so the same sequence works on every PC.
    _SALT = b"PitchPassKey/scrypt/v2"
    _SCRYPT_N = 2**15
    _SCRYPT_R = 8
    _SCRYPT_P = 1
    _SEED_LENGTH = 32

    _UPPER = string.ascii_uppercase
    _LOWER = string.ascii_lowercase
    _DIGITS = string.digits
    _SYMBOLS = "!@#$%^&*()-_=+[]{}:,.?"
    _ALPHABET = _UPPER + _LOWER + _DIGITS + _SYMBOLS

    def derive(self, sequence: NoteSequence, length: int) -> str:
        if not 12 <= length <= 128:
            raise ValueError("generated passwords must be between 12 and 128 characters")

        # No per-machine or per-installation secret is used. The canonical note
        # sequence and fixed public parameters make the result portable.
        seed = hashlib.scrypt(
            password=self._VERSION + sequence.canonical_bytes(),
            salt=self._SALT,
            n=self._SCRYPT_N,
            r=self._SCRYPT_R,
            p=self._SCRYPT_P,
            dklen=self._SEED_LENGTH,
        )

        chunks = [
            self._draw(seed, self._UPPER, 1, b"upper"),
            self._draw(seed, self._LOWER, 1, b"lower"),
            self._draw(seed, self._DIGITS, 1, b"digits"),
            self._draw(seed, self._SYMBOLS, 1, b"symbols"),
            self._draw(seed, self._ALPHABET, length - 4, b"body"),
        ]
        return self._deterministic_shuffle("".join(chunks), seed)

    @staticmethod
    def _blocks(seed: bytes, domain: bytes):
        counter = 0
        while True:
            yield hmac.new(seed, domain + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            counter += 1

    def _draw(self, seed: bytes, alphabet: str, count: int, domain: bytes) -> str:
        if count <= 0:
            return ""

        # Rejection sampling avoids modulo bias when mapping bytes to characters.
        limit = (256 // len(alphabet)) * len(alphabet)
        result: list[str] = []

        for block in self._blocks(seed, domain):
            for value in block:
                if value >= limit:
                    continue
                result.append(alphabet[value % len(alphabet)])
                if len(result) == count:
                    return "".join(result)

        raise RuntimeError("password derivation stream ended unexpectedly")

    def _deterministic_shuffle(self, value: str, seed: bytes) -> str:
        items = list(value)
        stream = iter(byte for block in self._blocks(seed, b"shuffle") for byte in block)

        for index in range(len(items) - 1, 0, -1):
            span = index + 1
            limit = (256 // span) * span

            while True:
                candidate = next(stream)
                if candidate < limit:
                    break

            swap_index = candidate % span
            items[index], items[swap_index] = items[swap_index], items[index]

        return "".join(items)
