from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from .models import NoteEvent, NoteSequence


NoteCallback = Callable[[NoteEvent], None]


class NoteInputSource(ABC):
    """Stable boundary for MIDI, future audio transcription, files, or other sources."""

    @abstractmethod
    def list_devices(self) -> list[str]:
        ...

    @abstractmethod
    def start(self, device_name: str, callback: NoteCallback) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        ...


class PasswordDerivationPort(ABC):
    """Application-facing boundary for deterministic password derivation."""

    @abstractmethod
    def derive(self, sequence: NoteSequence, context: str, length: int) -> str:
        ...
