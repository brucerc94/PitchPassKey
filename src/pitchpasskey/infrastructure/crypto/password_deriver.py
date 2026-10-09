from __future__ import annotations

import hashlib
import hmac
import string

from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.domain.ports import (
    DerivationProgressCallback,
    PasswordDerivationPort,
)


class PasswordDeriver(PasswordDerivationPort):
    """Deterministic, cross-machine password derivation from MIDI notes only."""

    _VERSION = b"PitchPassKey/password/v2"
    # Public fixed salt: stable across installations by design.
    # It separates this application/version; it is not a secret.
    _SALT = b"PitchPassKey/scrypt/v2"
    _SCRYPT_N = 2**15
    _SCRYPT_R = 8
    _SCRYPT_P = 1
    _SCRYPT_MAXMEM = 64 * 1024 * 1024
    _SEED_LENGTH = 32

    _UPPER = string.ascii_uppercase
    _LOWER = string.ascii_lowercase
    _DIGITS = string.digits
    _SYMBOLS = "!@#$%^&*()-_=+[]{}:,.?"
    _ALPHABET = _UPPER + _LOWER + _DIGITS + _SYMBOLS

    def derive(
        self,
        sequence: NoteSequence,
        length: int,
        progress_callback: DerivationProgressCallback | None = None,
    ) -> str:
        if not 12 <= length <= 128:
            raise ValueError("generated passwords must be between 12 and 128 characters")

        # Canonical representation contains only note number and note order.
        # Rhythm, velocity, duration and pedal state are intentionally ignored.
        canonical_input = self._VERSION + sequence.canonical_bytes()
        self._notify(progress_callback, "fingerprint")

        # scrypt is the real, intentionally expensive key-derivation step.
        self._notify(progress_callback, "scrypt")
        seed = hashlib.scrypt(
            password=canonical_input,
            salt=self._SALT,
            n=self._SCRYPT_N,
            r=self._SCRYPT_R,
            p=self._SCRYPT_P,
            maxmem=self._SCRYPT_MAXMEM,
            dklen=self._SEED_LENGTH,
        )

        # Expansion and shuffling are derived from the scrypt seed using HMAC.
        self._notify(progress_callback, "expand")
        chunks = [
            self._draw(seed, self._UPPER, 1, b"upper"),
            self._draw(seed, self._LOWER, 1, b"lower"),
            self._draw(seed, self._DIGITS, 1, b"digits"),
            self._draw(seed, self._SYMBOLS, 1, b"symbols"),
            self._draw(seed, self._ALPHABET, length - 4, b"body"),
        ]
        password = self._deterministic_shuffle("".join(chunks), seed)
        self._notify(progress_callback, "complete")
        return password

    @staticmethod
    def _notify(
        callback: DerivationProgressCallback | None,
        stage: str,
    ) -> None:
        if callback is not None:
            callback(stage)

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
