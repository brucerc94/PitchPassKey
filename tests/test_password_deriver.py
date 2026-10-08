from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.infrastructure.crypto.password_deriver import PasswordDeriver


class FakeSecretProvider:
    def get_or_create(self, profile: str) -> bytes:
        assert profile == "default"
        return b"x" * 32


def sequence() -> NoteSequence:
    return NoteSequence.from_iterable([60, 64, 67, 60, 64, 67, 72, 67])


def test_derivation_is_deterministic() -> None:
    deriver = PasswordDeriver(FakeSecretProvider())

    first = deriver.derive(sequence(), "example.com", 24)
    second = deriver.derive(sequence(), "example.com", 24)

    assert first == second
    assert len(first) == 24


def test_context_changes_output() -> None:
    deriver = PasswordDeriver(FakeSecretProvider())
    assert deriver.derive(sequence(), "one", 24) != deriver.derive(sequence(), "two", 24)


def test_sequence_order_changes_output() -> None:
    deriver = PasswordDeriver(FakeSecretProvider())
    first = sequence()
    second = NoteSequence.from_iterable([60, 64, 67, 60, 72, 67, 64, 67])
    assert deriver.derive(first, "", 24) != deriver.derive(second, "", 24)


def test_output_has_required_character_classes() -> None:
    deriver = PasswordDeriver(FakeSecretProvider())
    password = deriver.derive(sequence(), "", 32)

    assert any(char.isupper() for char in password)
    assert any(char.islower() for char in password)
    assert any(char.isdigit() for char in password)
    assert any(char in deriver._SYMBOLS for char in password)


def test_unicode_context_is_normalized() -> None:
    deriver = PasswordDeriver(FakeSecretProvider())
    assert deriver.derive(sequence(), "café", 24) == deriver.derive(sequence(), "cafe\u0301", 24)
