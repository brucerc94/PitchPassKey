from __future__ import annotations

import hashlib
import hmac
import string
from typing import Protocol

from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.domain.ports import PasswordDerivationPort


class SecretProvider(Protocol):
    """Infrastructure boundary for OS-backed secret stores."""

    def get_or_create(self, profile: str) -> bytes: ...


class PasswordDeriver(PasswordDerivationPort):
    """Deterministic HMAC-SHA-256 based password derivation."""

    _VERSION = b"PitchPassKey/password/v1"
    _UPPER = string.ascii_uppercase
    _LOWER = string.ascii_lowercase
    _DIGITS = string.digits
    _SYMBOLS = "!@#$%^&*()-_=+[]{}:,.?"
    _ALPHABET = _UPPER + _LOWER + _DIGITS + _SYMBOLS

    def __init__(self, secret_provider: SecretProvider, profile: str = "default") -> None:
        self._secret_provider = secret_provider
        self._profile = profile

    def derive(self, sequence: NoteSequence, length: int) -> str:
        if length < 12:
            raise ValueError("generated passwords must be at least 12 characters")

        secret = self._secret_provider.get_or_create(self._profile)
        payload = self._VERSION + sequence.canonical_bytes()
        seed = hmac.new(secret, payload, hashlib.sha256).digest()

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
