from __future__ import annotations

from threading import Lock
from typing import Any

import mido

from pitchpasskey.domain.models import NoteEvent
from pitchpasskey.domain.ports import NoteCallback, NoteInputSource


class MidiControllerInput(NoteInputSource):
    """MIDI controller adapter backed by mido/RTMIDI."""

    def __init__(self) -> None:
        self._port: Any | None = None
        self._lock = Lock()

    def list_devices(self) -> list[str]:
        return list(mido.get_input_names())

    def start(self, device_name: str, callback: NoteCallback) -> None:
        with self._lock:
            if self._port is not None:
                raise RuntimeError("MIDI input is already running")

            if device_name not in self.list_devices():
                raise ValueError("Selected MIDI device is no longer available")

            self._port = mido.open_input(device_name, callback=self._build_callback(callback))

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
            # Only note_on with a positive velocity represents a pressed key.
            # Velocity itself is never forwarded into the domain.
            if message.type != "note_on" or getattr(message, "velocity", 0) <= 0:
                return
            callback(NoteEvent(int(message.note)))

        return handle
