from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.application.password_service import PasswordService
from pitchpasskey.infrastructure.crypto.password_deriver import PasswordDeriver
from pitchpasskey.infrastructure.midi.midi_controller import MidiControllerInput
from pitchpasskey.infrastructure.secrets.keyring_secret_store import KeyringSecretStore
from pitchpasskey.presentation.ui import MainWindow


def create_window() -> MainWindow:
    """Build the application window without coupling the core to Qt."""
    source = MidiControllerInput()
    capture = SequenceCapture(source)
    secret_store = KeyringSecretStore()
    deriver = PasswordDeriver(secret_store)
    password_service = PasswordService(deriver)
    return MainWindow(capture, password_service)


def main() -> None:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("PitchPassKey")
    application.setOrganizationName("PitchPassKey")

    window = create_window()
    window.show()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
