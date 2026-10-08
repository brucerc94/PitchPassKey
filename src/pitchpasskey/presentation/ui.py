from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
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
        self.setMinimumSize(760, 540)
        self.resize(920, 620)

        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(30, 28, 30, 24)
        outer.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(14)

        mark = QLabel("P")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(44, 44)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        title = QLabel("PitchPassKey")
        title.setObjectName("title")

        subtitle = QLabel("Genera contraseñas deterministas a partir de una secuencia musical.")
        subtitle.setObjectName("subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        local_badge = QLabel("LOCAL")
        local_badge.setObjectName("badge")
        local_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        local_badge.setFixedWidth(62)

        header.addWidget(mark)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(local_badge, 0, Qt.AlignmentFlag.AlignTop)

        outer.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(18)

        input_group = QGroupBox("1  ·  ENTRADA")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(18, 20, 18, 18)
        input_layout.setSpacing(14)

        device_label = QLabel("Dispositivo MIDI")
        device_label.setObjectName("fieldLabel")

        device_row = QHBoxLayout()
        device_row.setSpacing(8)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(40)

        refresh_button = QPushButton("Actualizar")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.setMinimumHeight(40)
        refresh_button.clicked.connect(self.refresh_devices)

        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(refresh_button)

        self.record_button = QPushButton("Iniciar captura")
        self.record_button.setObjectName("primaryButton")
        self.record_button.setMinimumHeight(42)
        self.record_button.clicked.connect(self.toggle_capture)

        clear_button = QPushButton("Limpiar secuencia")
        clear_button.setObjectName("secondaryButton")
        clear_button.setMinimumHeight(38)
        clear_button.clicked.connect(self.clear_sequence)

        helper = QLabel("Solo se consideran la nota y su orden.")
        helper.setObjectName("hint")
        helper.setWordWrap(True)

        input_layout.addWidget(device_label)
        input_layout.addLayout(device_row)
        input_layout.addWidget(self.record_button)
        input_layout.addWidget(clear_button)
        input_layout.addStretch(1)
        input_layout.addWidget(helper)

        sequence_group = QGroupBox("2  ·  SECUENCIA")
        sequence_layout = QVBoxLayout(sequence_group)
        sequence_layout.setContentsMargins(18, 20, 18, 18)
        sequence_layout.setSpacing(10)

        sequence_hint = QLabel("Notas capturadas en orden")
        sequence_hint.setObjectName("fieldLabel")

        self.sequence_display = QLineEdit()
        self.sequence_display.setReadOnly(True)
        self.sequence_display.setPlaceholderText("C4  →  E4  →  G4  →  …")
        self.sequence_display.setMinimumHeight(42)

        sequence_font = QFont("Consolas")
        sequence_font.setPointSize(10)
        self.sequence_display.setFont(sequence_font)

        self.count_label = QLabel("0 notas")
        self.count_label.setObjectName("hint")

        sequence_layout.addWidget(sequence_hint)
        sequence_layout.addWidget(self.sequence_display)
        sequence_layout.addWidget(self.count_label)

        left_column = QVBoxLayout()
        left_column.setSpacing(18)
        left_column.addWidget(input_group)
        left_column.addWidget(sequence_group, 1)

        password_group = QGroupBox("3  ·  CONTRASEÑA")
        password_layout = QVBoxLayout(password_group)
        password_layout.setContentsMargins(18, 20, 18, 18)
        password_layout.setSpacing(14)

        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(10)

        self.length_combo = QComboBox()
        self.length_combo.addItems(["16", "20", "24", "32", "40", "48", "64"])
        self.length_combo.setCurrentText(str(self.password_service.policy.length))
        self.length_combo.setFixedWidth(92)
        self.length_combo.setMinimumHeight(40)

        settings.addRow("Longitud", self.length_combo)

        self.generate_button = QPushButton("Generar contraseña")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.setMinimumHeight(46)
        self.generate_button.clicked.connect(self.generate_password)

        password_layout.addLayout(settings)
        password_layout.addWidget(self.generate_button)

        password_label = QLabel("Resultado")
        password_label.setObjectName("fieldLabel")

        self.password_entry = QLineEdit()
        self.password_entry.setReadOnly(True)
        self.password_entry.setPlaceholderText("Genera una contraseña para verla aquí.")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setMinimumHeight(46)

        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_entry)

        password_actions = QHBoxLayout()
        password_actions.setSpacing(10)

        self.show_checkbox = QCheckBox("Mostrar")
        self.show_checkbox.toggled.connect(self.toggle_password_visibility)

        self.copy_button = QPushButton("Copiar contraseña")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setMinimumHeight(40)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_password)

        password_actions.addWidget(self.show_checkbox)
        password_actions.addStretch(1)
        password_actions.addWidget(self.copy_button)

        password_layout.addLayout(password_actions)
        password_layout.addStretch(1)

        security_frame = QFrame()
        security_frame.setObjectName("securityFrame")

        security_layout = QVBoxLayout(security_frame)
        security_layout.setContentsMargins(12, 10, 12, 10)

        security_title = QLabel("Protección local")
        security_title.setObjectName("securityTitle")

        security_text = QLabel(
            "La clave de perfil permanece en el almacén seguro del sistema. "
            "La contraseña se mantiene en memoria y se oculta por defecto."
        )
        security_text.setObjectName("securityText")
        security_text.setWordWrap(True)

        security_layout.addWidget(security_title)
        security_layout.addWidget(security_text)

        password_layout.addWidget(security_frame)

        content.addLayout(left_column, 1)
        content.addWidget(password_group, 1)

        outer.addLayout(content, 1)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        outer.addWidget(separator)

        self.status_label = QLabel("●  Listo")
        self.status_label.setObjectName("status")
        outer.addWidget(self.status_label)

        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #11161c;
            }

            QLabel {
                color: #e8edf2;
            }

            QLabel#brandMark {
                background: #2f6fed;
                color: #ffffff;
                border-radius: 12px;
                font-size: 23px;
                font-weight: 800;
            }

            QLabel#title {
                font-size: 25px;
                font-weight: 700;
                color: #f2f5f8;
            }

            QLabel#subtitle {
                font-size: 12px;
                color: #8996a5;
            }

            QLabel#badge {
                background: #19241f;
                color: #78d59a;
                border: 1px solid #2d5b42;
                border-radius: 11px;
                padding: 4px 8px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            QGroupBox {
                background: #181e25;
                border: 1px solid #2a333e;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 10px;
                color: #aeb9c5;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.6px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 7px;
                background: #11161c;
            }

            QLabel#fieldLabel {
                color: #bac5d1;
                font-size: 11px;
                font-weight: 600;
            }

            QComboBox,
            QLineEdit {
                background: #10151b;
                border: 1px solid #303b47;
                border-radius: 8px;
                padding: 8px 11px;
                color: #edf2f7;
                selection-background-color: #315fae;
            }

            QComboBox:hover,
            QLineEdit:hover {
                border-color: #465363;
            }

            QComboBox:focus,
            QLineEdit:focus {
                border: 1px solid #4f86f7;
            }

            QComboBox QAbstractItemView {
                background: #181e25;
                color: #edf2f7;
                border: 1px solid #34404c;
                selection-background-color: #2d5da8;
                selection-color: #ffffff;
            }

            QPushButton {
                min-height: 36px;
                padding: 0 13px;
                border-radius: 8px;
                border: 1px solid #303b47;
                background: #202731;
                color: #d7dee6;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #27303b;
                border-color: #43505e;
            }

            QPushButton:pressed {
                background: #1c232c;
            }

            QPushButton:disabled {
                color: #687583;
                background: #191f26;
                border-color: #28313b;
            }

            QPushButton#primaryButton {
                background: #3274e9;
                border: 1px solid #4b87f5;
                color: #ffffff;
            }

            QPushButton#primaryButton:hover {
                background: #3b7cf0;
            }

            QPushButton#primaryButton:pressed {
                background: #2c67d0;
            }

            QPushButton#secondaryButton {
                background: #1c232b;
            }

            QCheckBox {
                color: #9eabb9;
                spacing: 7px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #42505f;
                border-radius: 4px;
                background: #10151b;
            }

            QCheckBox::indicator:checked {
                background: #3274e9;
                border-color: #4b87f5;
            }

            QLabel#hint {
                color: #738190;
                font-size: 10px;
            }

            QFrame#securityFrame {
                background: #141b21;
                border: 1px solid #263540;
                border-radius: 9px;
            }

            QLabel#securityTitle {
                color: #91a0af;
                font-size: 10px;
                font-weight: 700;
            }

            QLabel#securityText {
                color: #687888;
                font-size: 10px;
            }

            QFrame#separator {
                color: #27313c;
            }

            QLabel#status {
                color: #738190;
                font-size: 10px;
            }
            """
        )

    def refresh_devices(self) -> None:
        try:
            devices = self.capture.list_devices()
        except MidiInputError as exc:
            self._set_status(f"●  No se pudieron leer los dispositivos MIDI: {exc}")
            return

        current_device = self.device_combo.currentText()
        self.device_combo.clear()
        self.device_combo.addItems(devices)

        if current_device in devices:
            self.device_combo.setCurrentText(current_device)

        if devices:
            self._set_status(f"●  {len(devices)} dispositivo(s) MIDI disponible(s).")
        else:
            self._set_status("●  No se detectó un dispositivo MIDI.")

    def toggle_capture(self) -> None:
        if self.capture.is_running:
            self.capture.stop()
            self.record_button.setText("Iniciar captura")
            self._set_status("●  Captura detenida.")
            return

        device = self.device_combo.currentText().strip()
        if not device:
            QMessageBox.warning(self, "MIDI", "Selecciona un dispositivo MIDI.")
            return

        try:
            self.capture.start(device)
            self.record_button.setText("Detener captura")
            self._set_status("●  Capturando notas…")
        except MidiInputError as exc:
            QMessageBox.critical(self, "MIDI", str(exc))
            self._set_status("●  Error de captura.")

    def clear_sequence(self) -> None:
        self.capture.clear()
        self._last_sequence = ()
        self._clear_password()
        self._refresh_sequence()
        self._set_status("●  Secuencia limpiada.")

    def generate_password(self) -> None:
        try:
            length = int(self.length_combo.currentText())
            password = self.password_service.generate(self.capture.sequence, length)

            self.password_entry.setText(password)
            self.copy_button.setEnabled(True)
            self._set_status("●  Contraseña generada y mantenida solo en memoria.")
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
        self._set_status("●  Contraseña copiada al portapapeles. Límpialo al terminar.")

    def _refresh_sequence(self) -> None:
        sequence = self.capture.sequence
        if sequence.notes == self._last_sequence:
            return

        self._last_sequence = sequence.notes
        names = sequence.display_names()
        self.sequence_display.setText("  →  ".join(names[-24:]) if names else "")
        suffix = "…" if len(names) > 24 else ""
        self.count_label.setText(f"{len(names)} notas{suffix}")

        if self.password_entry.text():
            self._clear_password()
            self._set_status("●  La secuencia cambió; genera una nueva contraseña.")

    def _clear_password(self) -> None:
        self.password_entry.clear()
        self.copy_button.setEnabled(False)

    def _set_status(self, value: str) -> None:
        self.status_label.setText(value)

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self.capture.stop()
        event.accept()
