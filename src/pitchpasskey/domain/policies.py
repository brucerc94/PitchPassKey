from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    length: int = 24
    min_sequence_length: int = 8
    max_sequence_length: int = 128
    max_context_length: int = 128

    def __post_init__(self) -> None:
        if not 12 <= self.length <= 128:
            raise ValueError("password length must be between 12 and 128")
        if not 1 <= self.min_sequence_length <= self.max_sequence_length:
            raise ValueError("invalid sequence length bounds")
        if not 0 <= self.max_context_length <= 1024:
            raise ValueError("invalid context length")
