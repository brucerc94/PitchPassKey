from __future__ import annotations

from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.domain.policies import PasswordPolicy
from pitchpasskey.domain.ports import PasswordDerivationPort


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
        context: str = "",
        length: int | None = None,
    ) -> str:
        if not self._policy.min_sequence_length <= len(sequence) <= self._policy.max_sequence_length:
            raise ValueError(
                f"sequence must contain {self._policy.min_sequence_length}-"
                f"{self._policy.max_sequence_length} notes"
            )

        normalized_context = context.strip()
        if len(normalized_context) > self._policy.max_context_length:
            raise ValueError("context is too long")

        output_length = length if length is not None else self._policy.length
        if not 12 <= output_length <= 128:
            raise ValueError("password length must be between 12 and 128")

        return self._deriver.derive(
            sequence=sequence,
            context=normalized_context,
            length=output_length,
        )
