from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.application.password_service import PasswordService
from pitchpasskey.infrastructure.midi.midi_controller import MidiInputError
from pitchpasskey.infrastructure.secrets.keyring_secret_store import SecretStoreError


class MainWindow(QMainWindow):
    """Professional desktop presentation layer built with Qt."""

    def __init__(
        self,
        capture: SequenceCapture,
        password_service: PasswordService,
    ) -> None:
        super().__init__()

        self.capture = capture
        self.password_service = password_service
        self._last_sequence: tuple[int, ...] = ()

        self._build()
        self.refresh_devices()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(100)
        self._refresh_timer.timeout.connect(self._refresh_sequence)
        self._refresh_timer.start()

    def _build(self) -> None:
        self.setWindowTitle("PitchPassKey")
        self.setMinimumSize(720, 560)
        self.resize(800, 620)

        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel("PitchPassKey")
        title.setObjectName("title")
        outer.addWidget(title)

        subtitle = QLabel("Genera una contraseña a partir de una secuencia musical.")
        subtitle.setObjectName("subtitle")
        outer.addWidget(subtitle)

        input_group = QGroupBox("Entrada MIDI")
        input_layout = QFormLayout(input_group)
        input_layout.setContentsMargins(18, 20, 18, 18)
        input_layout.setHorizontalSpacing(16)
        input_layout.setVerticalSpacing(12)

        device_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(360)

        refresh_button = QPushButton("Actualizar")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.clicked.connect(self.refresh_devices)

        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(refresh_button)
        input_layout.addRow("Dispositivo", device_row)

        capture_row = QHBoxLayout()

        self.record_button = QPushButton("Iniciar captura")
        self.record_button.setObjectName("primaryButton")
        self.record_button.clicked.connect(self.toggle_capture)

        clear_button = QPushButton("Limpiar")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(self.clear_sequence)

        capture_row.addWidget(self.record_button)
        capture_row.addWidget(clear_button)
        capture_row.addStretch(1)

        input_layout.addRow("", capture_row)

        hint = QLabel("Solo se consideran la nota y su orden. Velocidad, timing y duración no se utilizan.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        input_layout.addRow("", hint)

        outer.addWidget(input_group)

        sequence_group = QGroupBox("Secuencia capturada")
        sequence_layout = QVBoxLayout(sequence_group)
        sequence_layout.setContentsMargins(18, 20, 18, 18)
        sequence_layout.setSpacing(10)

        self.sequence_display = QLineEdit()
        self.sequence_display.setReadOnly(True)
        self.sequence_display.setPlaceholderText("Toca las notas en tu controlador MIDI.")
        self.sequence_display.setMinimumHeight(40)

        sequence_font = QFont("Consolas")
        sequence_font.setPointSize(10)
        self.sequence_display.setFont(sequence_font)

        self.count_label = QLabel("0 notas")
        self.count_label.setObjectName("hint")

        sequence_layout.addWidget(self.sequence_display)
        sequence_layout.addWidget(self.count_label)

        outer.addWidget(sequence_group)

        password_group = QGroupBox("Contraseña")
        password_layout = QVBoxLayout(password_group)
        password_layout.setContentsMargins(18, 20, 18, 18)
        password_layout.setSpacing(12)

        settings_row = QHBoxLayout()

        length_label = QLabel("Longitud")
        self.length_combo = QComboBox()
        self.length_combo.addItems(["16", "20", "24", "32", "40", "48", "64"])
        self.length_combo.setCurrentText(str(password_service.policy.length))
        self.length_combo.setFixedWidth(90)

        settings_row.addWidget(length_label)
        settings_row.addWidget(self.length_combo)
        settings_row.addStretch(1)

        self.generate_button = QPushButton("Generar contraseña")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(self.generate_password)
        settings_row.addWidget(self.generate_button)

        password_layout.addLayout(settings_row)

        password_row = QHBoxLayout()

        self.password_entry = QLineEdit()
        self.password_entry.setReadOnly(True)
        self.password_entry.setPlaceholderText("La contraseña aparecerá aquí.")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setMinimumHeight(40)

        self.show_checkbox = QCheckBox("Mostrar")
        self.show_checkbox.toggled.connect(self.toggle_password_visibility)

        self.copy_button = QPushButton("Copiar")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_password)

        password_row.addWidget(self.password_entry, 1)
        password_row.addWidget(self.show_checkbox)
        password_row.addWidget(self.copy_button)

        password_layout.addLayout(password_row)

        security_hint = QLabel("La contraseña se mantiene en memoria y se muestra oculta por defecto.")
        security_hint.setObjectName("hint")
        security_hint.setWordWrap(True)
        password_layout.addWidget(security_hint)

        outer.addWidget(password_group)
        outer.addStretch(1)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        outer.addWidget(separator)

        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("status")
        outer.addWidget(self.status_label)

        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f7fa;
            }

            QLabel#title {
                font-size: 28px;
                font-weight: 700;
                color: #16202a;
            }

            QLabel#subtitle {
                font-size: 13px;
                color: #617080;
                margin-bottom: 4px;
            }

            QGroupBox {
                background: #ffffff;
                border: 1px solid #d9e0e7;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 8px;
                font-size: 13px;
                font-weight: 600;
                color: #263442;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                background: #f5f7fa;
            }

            QComboBox,
            QLineEdit {
                background: #ffffff;
                border: 1px solid #c8d0d8;
                border-radius: 7px;
                padding: 7px 10px;
                color: #1f2933;
            }

            QComboBox:focus,
            QLineEdit:focus {
                border: 1px solid #5b8def;
            }

            QPushButton {
                min-height: 36px;
                padding: 0 14px;
                border-radius: 7px;
                border: 1px solid #c8d0d8;
                background: #ffffff;
                color: #263442;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #f0f3f7;
            }

            QPushButton:disabled {
                color: #9aa5b1;
                background: #eef1f4;
            }

            QPushButton#primaryButton {
                border: 1px solid #285ccf;
                background: #326fe6;
                color: #ffffff;
            }

            QPushButton#primaryButton:hover {
                background: #2b63cf;
            }

            QPushButton#secondaryButton {
                background: #ffffff;
            }

            QLabel#hint {
                color: #71808f;
                font-size: 11px;
            }

            QLabel#status {
                color: #566574;
                font-size: 11px;
            }

            QFrame#separator {
                color: #d9e0e7;
            }

            QCheckBox {
                color: #566574;
                spacing: 6px;
            }
            """
        )

    def refresh_devices(self) -> None:
        try:
            devices = self.capture.list_devices()
        except MidiInputError as exc:
            self._set_status(f"No se pudieron leer los dispositivos MIDI: {exc}")
            return

        current_device = self.device_combo.currentText()
        self.device_combo.clear()
        self.device_combo.addItems(devices)

        if current_device in devices:
            self.device_combo.setCurrentText(current_device)

        if devices:
            self._set_status(f"{len(devices)} dispositivo(s) MIDI disponible(s).")
        else:
            self._set_status("No se detectó un dispositivo MIDI.")

    def toggle_capture(self) -> None:
        if self.capture.is_running:
            self.capture.stop()
            self.record_button.setText("Iniciar captura")
            self._set_status("Captura detenida.")
            return

        device = self.device_combo.currentText().strip()
        if not device:
            QMessageBox.warning(self, "MIDI", "Selecciona un dispositivo MIDI.")
            return

        try:
            self.capture.start(device)
            self.record_button.setText("Detener captura")
            self._set_status("Capturando notas…")
        except MidiInputError as exc:
            QMessageBox.critical(self, "MIDI", str(exc))
            self._set_status("Error de captura.")

    def clear_sequence(self) -> None:
        self.capture.clear()
        self._last_sequence = ()
        self._clear_password()
        self._refresh_sequence()
        self._set_status("Secuencia limpiada.")

    def generate_password(self) -> None:
        try:
            length = int(self.length_combo.currentText())
            password = self.password_service.generate(self.capture.sequence, length)

            self.password_entry.setText(password)
            self.copy_button.setEnabled(True)
            self._set_status("Contraseña generada y mantenida solo en memoria.")
        except (ValueError, SecretStoreError) as exc:
            QMessageBox.warning(self, "No se pudo generar", str(exc))

    def toggle_password_visibility(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password_entry.setEchoMode(mode)

    def copy_password(self) -> None:
        value = self.password_entry.text()
        if not value:
            return

        QApplication.clipboard().setText(value)
        self._set_status("Contraseña copiada al portapapeles. Límpialo al terminar.")

    def _refresh_sequence(self) -> None:
        sequence = self.capture.sequence
        if sequence.notes == self._last_sequence:
            return

        self._last_sequence = sequence.notes
        names = sequence.display_names()
        self.sequence_display.setText(" → ".join(names[-24:]) if names else "")
        suffix = "…" if len(names) > 24 else ""
        self.count_label.setText(f"{len(names)} notas{suffix}")

        if self.password_entry.text():
            self._clear_password()
            self._set_status("La secuencia cambió; genera una nueva contraseña.")

    def _clear_password(self) -> None:
        self.password_entry.clear()
        self.copy_button.setEnabled(False)

    def _set_status(self, value: str) -> None:
        self.status_label.setText(value)

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self.capture.stop()
        event.accept()
