from pitchpasskey.domain.models import NoteEvent, NoteSequence


def test_note_event_accepts_midi_range() -> None:
    assert NoteEvent(0).midi_note == 0
    assert NoteEvent(127).midi_note == 127


def test_note_sequence_rejects_out_of_range() -> None:
    for note in (-1, 128):
        try:
            NoteEvent(note)
        except ValueError:
            continue
        raise AssertionError("Expected ValueError")


def test_note_sequence_preserves_order() -> None:
    sequence = NoteSequence.from_iterable([60, 64, 67])
    assert tuple(sequence) == (60, 64, 67)
    assert sequence.display_names() == ("C4", "E4", "G4")


def test_note_sequence_is_immutable() -> None:
    sequence = NoteSequence.from_iterable([60, 64])
    extended = sequence.append(67)
    assert tuple(sequence) == (60, 64)
    assert tuple(extended) == (60, 64, 67)


def test_canonical_bytes_are_stable() -> None:
    left = NoteSequence.from_iterable([60, 64, 67]).canonical_bytes()
    right = NoteSequence.from_iterable([60, 64, 67]).canonical_bytes()
    assert left == right
