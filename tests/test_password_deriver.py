from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.infrastructure.crypto.password_deriver import PasswordDeriver


def sequence() -> NoteSequence:
    return NoteSequence.from_iterable([60, 64, 67, 60, 64, 67, 72, 67])


def test_same_sequence_reproduces_password_across_instances() -> None:
    first = PasswordDeriver().derive(sequence(), 24)
    second = PasswordDeriver().derive(sequence(), 24)

    assert first == second
    assert len(first) == 24


def test_sequence_order_changes_output() -> None:
    first = sequence()
    second = NoteSequence.from_iterable([60, 64, 67, 60, 72, 67, 64, 67])

    assert PasswordDeriver().derive(first, 24) != PasswordDeriver().derive(second, 24)


def test_output_has_required_character_classes() -> None:
    password = PasswordDeriver().derive(sequence(), 32)

    assert any(char.isupper() for char in password)
    assert any(char.islower() for char in password)
    assert any(char.isdigit() for char in password)
    assert any(char in PasswordDeriver._SYMBOLS for char in password)


def test_different_sequence_changes_output() -> None:
    first = sequence()
    second = NoteSequence.from_iterable([60, 64, 67, 62, 64, 67, 72, 67])

    assert PasswordDeriver().derive(first, 24) != PasswordDeriver().derive(second, 24)


def test_supported_password_length_bounds() -> None:
    deriver = PasswordDeriver()
    assert len(deriver.derive(sequence(), 12)) == 12
    assert len(deriver.derive(sequence(), 128)) == 128


def test_invalid_length_is_rejected() -> None:
    deriver = PasswordDeriver()

    for length in (0, 11, 129):
        try:
            deriver.derive(sequence(), length)
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for length {length}")


def test_progress_callback_reports_real_derivation_stages() -> None:
    stages: list[str] = []

    PasswordDeriver().derive(sequence(), 24, progress_callback=stages.append)

    assert stages == ["fingerprint", "scrypt", "expand", "complete"]
