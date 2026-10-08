from __future__ import annotations

from threading import Lock
from typing import Any

import mido

from pitchpasskey.domain.models import NoteEvent
from pitchpasskey.domain.ports import NoteCallback, NoteInputSource


class MidiInputError(RuntimeError):
    """Raised when the MIDI backend cannot provide the requested input."""


class MidiControllerInput(NoteInputSource):
    """MIDI controller adapter backed by mido/RTMIDI."""

    def __init__(self) -> None:
        self._port: Any | None = None
        self._lock = Lock()

    def list_devices(self) -> list[str]:
        try:
            return list(mido.get_input_names())
        except (OSError, RuntimeError) as exc:
            raise MidiInputError(f"Could not enumerate MIDI devices: {exc}") from exc

    def start(self, device_name: str, callback: NoteCallback) -> None:
        with self._lock:
            if self._port is not None:
                raise MidiInputError("MIDI input is already running")

            if device_name not in self.list_devices():
                raise MidiInputError("Selected MIDI device is no longer available")

            try:
                self._port = mido.open_input(
                    device_name,
                    callback=self._build_callback(callback),
                )
            except (OSError, RuntimeError) as exc:
                raise MidiInputError(f"Could not open MIDI device: {exc}") from exc

    def stop(self) -> None:
        with self._lock:
            port = self._port
            self._port = None

        if port is not None:
            port.close()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._port is not None

    @staticmethod
    def _build_callback(callback: NoteCallback):
        def handle(message: Any) -> None:
            # MIDI note_on with velocity=0 is note_off.
            # Velocity itself never enters the domain.
            if message.type != "note_on" or getattr(message, "velocity", 0) <= 0:
                return
            callback(NoteEvent(int(message.note)))

        return handle
