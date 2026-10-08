from __future__ import annotations

from threading import Lock

from pitchpasskey.domain.models import NoteEvent, NoteSequence
from pitchpasskey.domain.ports import NoteInputSource


class SequenceCapture:
    """Collect note events from any NoteInputSource."""

    def __init__(self, source: NoteInputSource) -> None:
        self._source = source
        self._lock = Lock()
        self._sequence = NoteSequence(())

    def list_devices(self) -> list[str]:
        return self._source.list_devices()

    @property
    def sequence(self) -> NoteSequence:
        with self._lock:
            return self._sequence

    def start(self, device_name: str) -> None:
        self._source.start(device_name, self._handle_note)

    def stop(self) -> None:
        self._source.stop()

    @property
    def is_running(self) -> bool:
        return self._source.is_running

    def clear(self) -> None:
        with self._lock:
            self._sequence = NoteSequence(())

    def _handle_note(self, event: NoteEvent) -> None:
        with self._lock:
            self._sequence = self._sequence.append(event.midi_note)
