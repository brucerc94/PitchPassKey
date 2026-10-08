from __future__ import annotations

import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoteEvent:
    """Normalized musical input event. Only note number enters the password domain."""

    midi_note: int

    def __post_init__(self) -> None:
        if not isinstance(self.midi_note, int):
            raise TypeError("midi_note must be an int")
        if not 0 <= self.midi_note <= 127:
            raise ValueError("midi_note must be between 0 and 127")


@dataclass(frozen=True, slots=True)
class NoteSequence:
    """Immutable ordered MIDI-note sequence."""

    notes: tuple[int, ...]

    def __post_init__(self) -> None:
        normalized = tuple(self.notes)
        for note in normalized:
            NoteEvent(note)
        object.__setattr__(self, "notes", normalized)

    @classmethod
    def from_iterable(cls, notes: Iterable[int]) -> NoteSequence:
        return cls(tuple(notes))

    def __len__(self) -> int:
        return len(self.notes)

    def __iter__(self) -> Iterator[int]:
        return iter(self.notes)

    def append(self, note: int) -> NoteSequence:
        NoteEvent(note)
        return NoteSequence(self.notes + (note,))

    def display_names(self) -> tuple[str, ...]:
        names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        return tuple(f"{names[n % 12]}{n // 12 - 1}" for n in self.notes)

    def canonical_bytes(self) -> bytes:
        return b"PPK1" + struct.pack(">I", len(self.notes)) + bytes(self.notes)
