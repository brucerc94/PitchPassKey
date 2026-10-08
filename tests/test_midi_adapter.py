from mido import Message

from pitchpasskey.infrastructure.midi.midi_controller import MidiControllerInput


def test_note_callback_discards_note_off_and_keeps_note_number_only() -> None:
    received = []
    callback = MidiControllerInput._build_callback(received.append)

    callback(Message("note_on", note=60, velocity=110, time=3.2))
    callback(Message("note_on", note=60, velocity=0, time=0.1))
    callback(Message("note_off", note=64, velocity=90, time=0.2))

    assert len(received) == 1
    assert received[0].midi_note == 60
