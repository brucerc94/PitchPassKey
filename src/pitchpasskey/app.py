from __future__ import annotations

import tkinter as tk

from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.application.password_service import PasswordService
from pitchpasskey.infrastructure.crypto.password_deriver import PasswordDeriver
from pitchpasskey.infrastructure.midi.midi_controller import MidiControllerInput
from pitchpasskey.infrastructure.secrets.keyring_secret_store import KeyringSecretStore
from pitchpasskey.presentation.ui import MainWindow


def create_app() -> MainWindow:
    source = MidiControllerInput()
    capture = SequenceCapture(source)
    secret_store = KeyringSecretStore()
    deriver = PasswordDeriver(secret_store)
    password_service = PasswordService(deriver)

    root = tk.Tk()
    return MainWindow(root, capture, password_service)


def main() -> None:
    create_app().root.mainloop()
