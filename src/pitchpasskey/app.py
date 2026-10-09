from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.application.password_service import PasswordService
from pitchpasskey.infrastructure.crypto.password_deriver import PasswordDeriver
from pitchpasskey.infrastructure.midi.midi_controller import MidiControllerInput
from pitchpasskey.presentation.ui import MainWindow


def create_window() -> MainWindow:
    """Build the application window without coupling the core to Qt."""
    source = MidiControllerInput()
    capture = SequenceCapture(source)
    deriver = PasswordDeriver()
    password_service = PasswordService(deriver)
    return MainWindow(capture, password_service)


def main() -> None:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("PitchPassKey")
    application.setOrganizationName("PitchPassKey")

    icon_path = Path(__file__).resolve().parents[2] / "assets" / "pitchpasskey.svg"
    if icon_path.exists():
        application.setWindowIcon(QIcon(str(icon_path)))

    window = create_window()
    window.show()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
