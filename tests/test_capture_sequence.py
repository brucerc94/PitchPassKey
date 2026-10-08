from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.domain.models import NoteEvent


class FakeInput:
    def __init__(self) -> None:
        self.running = False
        self.callback = None

    def list_devices(self) -> list[str]:
        return ["fake-midi"]

    def start(self, device_name: str, callback) -> None:
        assert device_name == "fake-midi"
        self.running = True
        self.callback = callback

    def stop(self) -> None:
        self.running = False

    @property
    def is_running(self) -> bool:
        return self.running


def test_capture_is_bounded_and_preserves_order() -> None:
    source = FakeInput()
    capture = SequenceCapture(source, max_length=3)
    capture.start("fake-midi")

    source.callback(NoteEvent(60))
    source.callback(NoteEvent(64))
    source.callback(NoteEvent(67))
    source.callback(NoteEvent(72))

    assert capture.sequence.notes == (60, 64, 67)
