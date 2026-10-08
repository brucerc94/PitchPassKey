from __future__ import annotations

from pitchpasskey.domain.ports import NoteCallback, NoteInputSource


class AudioTranscriptionInput(NoteInputSource):
    """Reserved adapter for the user's future audio-to-note transcription project."""

    def list_devices(self) -> list[str]:
        return []

    def start(self, device_name: str, callback: NoteCallback) -> None:
        raise NotImplementedError(
            "Audio transcription is intentionally not implemented in PitchPassKey yet. "
            "Connect the future transcription engine through this adapter."
        )

    def stop(self) -> None:
        return None

    @property
    def is_running(self) -> bool:
        return False
