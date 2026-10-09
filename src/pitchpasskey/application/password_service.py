from __future__ import annotations

from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.domain.policies import PasswordPolicy
from pitchpasskey.domain.ports import (
    DerivationProgressCallback,
    PasswordDerivationPort,
)


class PasswordService:
    """Application use case for validated deterministic password generation."""

    def __init__(
        self,
        deriver: PasswordDerivationPort,
        policy: PasswordPolicy | None = None,
    ) -> None:
        self._deriver = deriver
        self._policy = policy or PasswordPolicy()

    @property
    def policy(self) -> PasswordPolicy:
        return self._policy

    def generate(
        self,
        sequence: NoteSequence,
        length: int | None = None,
        progress_callback: DerivationProgressCallback | None = None,
    ) -> str:
        sequence_length = len(sequence)
        if not self._policy.min_sequence_length <= sequence_length <= self._policy.max_sequence_length:
            raise ValueError(
                f"sequence must contain {self._policy.min_sequence_length}-"
                f"{self._policy.max_sequence_length} notes"
            )

        output_length = length if length is not None else self._policy.length
        if not 12 <= output_length <= 128:
            raise ValueError("password length must be between 12 and 128")

        if progress_callback is None:
            return self._deriver.derive(sequence=sequence, length=output_length)

        return self._deriver.derive(
            sequence=sequence,
            length=output_length,
            progress_callback=progress_callback,
        )
