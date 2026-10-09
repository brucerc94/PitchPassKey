from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QRectF, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen
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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.application.password_service import PasswordService
from pitchpasskey.domain.models import NoteSequence
from pitchpasskey.infrastructure.midi.midi_controller import MidiInputError


class PianoKeyboard(QWidget):
    """Painted piano keyboard that highlights captured MIDI notes."""

    _WHITE_PITCH_CLASSES = {0, 2, 4, 5, 7, 9, 11}
    _BLACK_PITCH_CLASSES = {1, 3, 6, 8, 10}
    _NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._sequence: tuple[int, ...] = ()
        self._visible_start = 48  # C3; three octaves are drawn at a time.
        self._pulse_frames = 0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(36)
        self._pulse_timer.timeout.connect(self._advance_pulse)

    @staticmethod
    def note_name(midi_note: int) -> str:
        name = PianoKeyboard._NOTE_NAMES[midi_note % 12]
        octave = midi_note // 12 - 1
        return f"{name}{octave}"

    def set_sequence(self, notes: tuple[int, ...]) -> None:
        normalized = tuple(notes)
        if normalized == self._sequence:
            return

        self._sequence = normalized
        if normalized:
            latest = normalized[-1]
            if not self._visible_start <= latest < min(self._visible_start + 36, 128):
                octave_start = (latest // 12) * 12 - 12
                self._visible_start = max(0, min(96, octave_start))

            self._pulse_frames = 12
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self._visible_start = 48

        self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize

        return QSize(470, 160)

    def _advance_pulse(self) -> None:
        if self._pulse_frames <= 0:
            self._pulse_timer.stop()
            return
        self._pulse_frames -= 1
        self.update()
        if self._pulse_frames == 0:
            self._pulse_timer.stop()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        background = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
        background.setColorAt(0.0, QColor("#111d2b"))
        background.setColorAt(1.0, QColor("#0b1119"))
        painter.setPen(QPen(QColor("#263a50"), 1.0))
        painter.setBrush(background)
        painter.drawRoundedRect(bounds, 12, 12)

        keyboard_rect = bounds.adjusted(10, 10, -10, -10)
        if keyboard_rect.width() <= 0 or keyboard_rect.height() <= 0:
            return

        visible_end = min(self._visible_start + 36, 128)
        visible_notes = list(range(self._visible_start, visible_end))
        white_notes = [
            note for note in visible_notes
            if note % 12 in self._WHITE_PITCH_CLASSES
        ]
        if not white_notes:
            return

        active_notes = set(self._sequence)
        latest_note = self._sequence[-1] if self._sequence else None
        white_width = keyboard_rect.width() / len(white_notes)
        key_height = keyboard_rect.height()
        key_font = QFont("Segoe UI", 7)
        key_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(key_font)

        # Draw the white keys first, leaving a narrow dark gap between them.
        for index, midi_note in enumerate(white_notes):
            rect = QRectF(
                keyboard_rect.left() + index * white_width + 1.0,
                keyboard_rect.top(),
                max(1.0, white_width - 2.0),
                key_height,
            )
            is_latest = midi_note == latest_note
            is_active = midi_note in active_notes

            if is_latest:
                fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                fill.setColorAt(0.0, QColor("#76e8ff"))
                fill.setColorAt(1.0, QColor("#3b83ff"))
                border = QColor("#a1f1ff")
            elif is_active:
                fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                fill.setColorAt(0.0, QColor("#c4d9ff"))
                fill.setColorAt(1.0, QColor("#6d91e8"))
                border = QColor("#91b6ff")
            else:
                fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                fill.setColorAt(0.0, QColor("#f4f7fc"))
                fill.setColorAt(1.0, QColor("#b5c5d8"))
                border = QColor("#8b9bb0")

            painter.setPen(QPen(border, 1.0))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 4, 4)

            if is_latest and self._pulse_frames:
                phase = (12 - self._pulse_frames) / 12
                glow_alpha = int(70 + 155 * math.sin(phase * math.pi))
                painter.setPen(QPen(QColor(83, 226, 255, glow_alpha), 2.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 5, 5)

            label = self.note_name(midi_note)
            painter.setPen(QColor("#08223d" if is_latest else "#26384d"))
            label_rect = QRectF(rect.left(), rect.bottom() - 18, rect.width(), 15)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

        # Black keys are painted last so they sit above the white keys.
        black_width = max(8.0, white_width * 0.58)
        black_height = key_height * 0.63
        for midi_note in visible_notes:
            if midi_note % 12 not in self._BLACK_PITCH_CLASSES:
                continue

            before_count = sum(1 for white_note in white_notes if white_note < midi_note)
            center_x = keyboard_rect.left() + before_count * white_width
            rect = QRectF(
                center_x - black_width / 2,
                keyboard_rect.top(),
                black_width,
                black_height,
            )
            is_latest = midi_note == latest_note
            is_active = midi_note in active_notes

            if is_latest:
                fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                fill.setColorAt(0.0, QColor("#68e1ff"))
                fill.setColorAt(1.0, QColor("#2459cb"))
                border = QColor("#a1f1ff")
            elif is_active:
                fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                fill.setColorAt(0.0, QColor("#6386d5"))
                fill.setColorAt(1.0, QColor("#172e60"))
                border = QColor("#78a4ff")
            else:
                fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                fill.setColorAt(0.0, QColor("#334154"))
                fill.setColorAt(1.0, QColor("#101723"))
                border = QColor("#080d14")

            painter.setPen(QPen(border, 1.0))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 3, 3)

            if is_latest and self._pulse_frames:
                phase = (12 - self._pulse_frames) / 12
                glow_alpha = int(70 + 155 * math.sin(phase * math.pi))
                painter.setPen(QPen(QColor(83, 226, 255, glow_alpha), 2.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 4, 4)


class _PasswordWorker(QThread):
    """Run the expensive derivation off the UI thread and report real stages."""

    progress = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        service: PasswordService,
        sequence: NoteSequence,
        length: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._sequence = sequence
        self._length = length

    def run(self) -> None:
        try:
            result = self._service.generate(
                self._sequence,
                self._length,
                progress_callback=self.progress.emit,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)


class MainWindow(QMainWindow):
    """Animated Qt interface for musical capture and password derivation."""

    _STAGE_INDEX = {
        "fingerprint": 0,
        "scrypt": 1,
        "expand": 2,
        "complete": 3,
    }
    _STAGE_MESSAGES = {
        "idle": "Ready for your musical sequence",
        "fingerprint": "Canonical musical fingerprint prepared",
        "scrypt": "Deriving the cryptographic seed with scrypt",
        "expand": "Expanding the result with HMAC-SHA-256",
        "complete": "Password generated successfully",
    }

    def __init__(
        self,
        capture: SequenceCapture,
        password_service: PasswordService,
    ) -> None:
        super().__init__()

        self.capture = capture
        self.password_service = password_service
        self._last_sequence: tuple[int, ...] = ()
        self._worker: _PasswordWorker | None = None

        self._build()
        self.refresh_devices()
        self._set_pipeline_stage("idle")

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(75)
        self._refresh_timer.timeout.connect(self._refresh_sequence)
        self._refresh_timer.start()

    def _build(self) -> None:
        self.setWindowTitle("PitchPassKey")
        self.setMinimumSize(900, 760)
        self.resize(1080, 850)

        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(26, 24, 26, 22)
        outer.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(14)

        logo_label = QLabel()
        logo_label.setObjectName("brandLogo")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedSize(64, 64)

        icon_path = Path(__file__).resolve().parents[3] / "assets" / "pitchpasskey.svg"
        app_icon = QIcon(str(icon_path))
        if not app_icon.isNull():
            logo_label.setPixmap(app_icon.pixmap(58, 58))

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("PitchPassKey")
        title.setObjectName("title")

        subtitle = QLabel("Your musical fingerprint. A repeatable password.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        local_badge = QLabel("LOCAL")
        local_badge.setObjectName("badge")
        local_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        local_badge.setFixedWidth(62)

        header.addWidget(logo_label)
        header.addLayout(title_box, 1)
        header.addStretch(1)
        header.addWidget(local_badge, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)

        # Left column: MIDI input, animated piano, and the captured note ribbon.
        left_column = QVBoxLayout()
        left_column.setSpacing(12)

        input_group = QGroupBox("01  ·  MIDI INPUT")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(16, 20, 16, 14)
        input_layout.setSpacing(10)

        device_label = QLabel("Input device")
        device_label.setObjectName("fieldLabel")

        device_row = QHBoxLayout()
        device_row.setSpacing(8)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(38)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setMinimumHeight(38)
        self.refresh_button.clicked.connect(self.refresh_devices)

        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.refresh_button)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.record_button = QPushButton("Start capture")
        self.record_button.setObjectName("primaryButton")
        self.record_button.setMinimumHeight(40)
        self.record_button.clicked.connect(self.toggle_capture)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("secondaryButton")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self.clear_sequence)

        action_row.addWidget(self.record_button, 1)
        action_row.addWidget(self.clear_button)

        input_hint = QLabel(
            "Capture notes from your MIDI controller. Rhythm, note duration, "
            "velocity and sustain pedal are ignored."
        )
        input_hint.setObjectName("hint")
        input_hint.setWordWrap(True)

        input_layout.addWidget(device_label)
        input_layout.addLayout(device_row)
        input_layout.addLayout(action_row)
        input_layout.addWidget(input_hint)
        left_column.addWidget(input_group)

        keyboard_group = QGroupBox("02  ·  LIVE PIANO")
        keyboard_layout = QVBoxLayout(keyboard_group)
        keyboard_layout.setContentsMargins(12, 18, 12, 12)
        keyboard_layout.setSpacing(8)

        keyboard_header = QHBoxLayout()
        keyboard_title = QLabel("Your notes light up as you play")
        keyboard_title.setObjectName("fieldLabel")
        self.keyboard_state_label = QLabel("WAITING FOR INPUT")
        self.keyboard_state_label.setObjectName("microBadge")
        keyboard_header.addWidget(keyboard_title, 1)
        keyboard_header.addWidget(self.keyboard_state_label)

        self.piano_keyboard = PianoKeyboard()

        keyboard_layout.addLayout(keyboard_header)
        keyboard_layout.addWidget(self.piano_keyboard)
        left_column.addWidget(keyboard_group)

        sequence_group = QGroupBox("03  ·  MUSICAL SEQUENCE")
        sequence_layout = QVBoxLayout(sequence_group)
        sequence_layout.setContentsMargins(14, 18, 14, 12)
        sequence_layout.setSpacing(8)

        sequence_header = QHBoxLayout()
        sequence_description = QLabel("Notes in the exact order captured")
        sequence_description.setObjectName("fieldLabel")
        self.count_label = QLabel("0 notes")
        self.count_label.setObjectName("countBadge")
        sequence_header.addWidget(sequence_description, 1)
        sequence_header.addWidget(self.count_label)
        sequence_layout.addLayout(sequence_header)

        self.sequence_scroll = QScrollArea()
        self.sequence_scroll.setObjectName("sequenceScroll")
        self.sequence_scroll.setWidgetResizable(False)
        self.sequence_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sequence_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sequence_scroll.setFixedHeight(58)

        self.sequence_strip = QWidget()
        self.sequence_strip.setObjectName("sequenceStrip")
        self.sequence_strip.setFixedHeight(42)
        self.sequence_strip_layout = QHBoxLayout(self.sequence_strip)
        self.sequence_strip_layout.setContentsMargins(4, 4, 4, 4)
        self.sequence_strip_layout.setSpacing(6)
        self.sequence_scroll.setWidget(self.sequence_strip)

        sequence_layout.addWidget(self.sequence_scroll)
        left_column.addWidget(sequence_group)
        left_column.addStretch(1)

        # Right column: an honest stage-by-stage view of the real algorithm.
        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        pipeline_group = QGroupBox("04  ·  DERIVATION ENGINE")
        pipeline_layout = QVBoxLayout(pipeline_group)
        pipeline_layout.setContentsMargins(16, 20, 16, 14)
        pipeline_layout.setSpacing(10)

        pipeline_top = QHBoxLayout()
        pipeline_top.setSpacing(8)

        pipeline_icon = QLabel("✦")
        pipeline_icon.setObjectName("pipelineIcon")
        pipeline_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pipeline_icon.setFixedSize(34, 34)

        self.pipeline_heading = QLabel("Ready for your musical sequence")
        self.pipeline_heading.setObjectName("pipelineHeading")
        self.pipeline_heading.setWordWrap(True)

        pipeline_top.addWidget(pipeline_icon)
        pipeline_top.addWidget(self.pipeline_heading, 1)
        pipeline_layout.addLayout(pipeline_top)

        self.pipeline_progress = QProgressBar()
        self.pipeline_progress.setObjectName("pipelineProgress")
        self.pipeline_progress.setRange(0, 100)
        self.pipeline_progress.setValue(0)
        self.pipeline_progress.setTextVisible(False)
        self.pipeline_progress.setFixedHeight(6)
        pipeline_layout.addWidget(self.pipeline_progress)

        self._pipeline_cards: dict[str, QFrame] = {}
        pipeline_steps = [
            ("fingerprint", "01", "Musical fingerprint", "Encode note numbers in their order"),
            ("scrypt", "02", "scrypt derivation", "Compute the fixed, portable seed"),
            ("expand", "03", "HMAC-SHA-256 expansion", "Build and shuffle password characters"),
            ("complete", "04", "Password ready", "Reveal or copy it when you choose"),
        ]

        for key, number, heading, description in pipeline_steps:
            step_frame = QFrame()
            step_frame.setObjectName("pipelineStep")
            step_frame.setProperty("stepState", "idle")
            step_layout = QHBoxLayout(step_frame)
            step_layout.setContentsMargins(10, 9, 10, 9)
            step_layout.setSpacing(10)

            number_badge = QLabel(number)
            number_badge.setObjectName("stepNumber")
            number_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number_badge.setFixedSize(32, 32)

            copy_layout = QVBoxLayout()
            copy_layout.setSpacing(2)

            step_title = QLabel(heading)
            step_title.setObjectName("stepTitle")

            step_description = QLabel(description)
            step_description.setObjectName("stepDescription")
            step_description.setWordWrap(True)

            copy_layout.addWidget(step_title)
            copy_layout.addWidget(step_description)

            step_layout.addWidget(number_badge)
            step_layout.addLayout(copy_layout, 1)
            pipeline_layout.addWidget(step_frame)
            self._pipeline_cards[key] = step_frame

        right_column.addWidget(pipeline_group)

        password_group = QGroupBox("05  ·  PASSWORD OUTPUT")
        password_layout = QVBoxLayout(password_group)
        password_layout.setContentsMargins(16, 20, 16, 14)
        password_layout.setSpacing(11)

        settings = QFormLayout()
        settings.setHorizontalSpacing(14)
        settings.setVerticalSpacing(8)

        self.length_combo = QComboBox()
        self.length_combo.addItems(["16", "20", "24", "32", "40", "48", "64"])
        self.length_combo.setCurrentText(str(self.password_service.policy.length))
        self.length_combo.setFixedWidth(94)
        self.length_combo.setMinimumHeight(38)
        settings.addRow("Password length", self.length_combo)

        self.generate_button = QPushButton("Generate password")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.setMinimumHeight(44)
        self.generate_button.clicked.connect(self.generate_password)

        password_label = QLabel("Generated result")
        password_label.setObjectName("fieldLabel")

        self.password_entry = QLineEdit()
        self.password_entry.setReadOnly(True)
        self.password_entry.setPlaceholderText("Your password will appear here.")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setMinimumHeight(44)
        self.password_entry.setFont(QFont("Consolas", 11))

        password_actions = QHBoxLayout()
        password_actions.setSpacing(8)

        self.show_checkbox = QCheckBox("Reveal")
        self.show_checkbox.toggled.connect(self.toggle_password_visibility)

        self.copy_button = QPushButton("Copy password")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setMinimumHeight(38)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_password)

        password_actions.addWidget(self.show_checkbox)
        password_actions.addStretch(1)
        password_actions.addWidget(self.copy_button)

        password_layout.addLayout(settings)
        password_layout.addWidget(self.generate_button)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_entry)
        password_layout.addLayout(password_actions)

        security_frame = QFrame()
        security_frame.setObjectName("securityFrame")
        security_layout = QVBoxLayout(security_frame)
        security_layout.setContentsMargins(12, 10, 12, 10)
        security_layout.setSpacing(4)

        security_title = QLabel("PORTABLE BY DESIGN")
        security_title.setObjectName("securityTitle")

        security_text = QLabel(
            "No machine-specific key or profile file is required. "
            "The same note sequence and length produce the same result."
        )
        security_text.setObjectName("securityText")
        security_text.setWordWrap(True)

        security_layout.addWidget(security_title)
        security_layout.addWidget(security_text)
        password_layout.addWidget(security_frame)

        right_column.addWidget(password_group, 1)

        content.addLayout(left_column, 11)
        content.addLayout(right_column, 10)
        outer.addLayout(content, 1)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        outer.addWidget(separator)

        self.status_label = QLabel("●  Ready")
        self.status_label.setObjectName("status")
        outer.addWidget(self.status_label)

        self._apply_style()
        self._render_sequence(())

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0d1219;
            }

            QLabel {
                color: #e8edf5;
            }

            QLabel#brandLogo {
                background: #101b2a;
                border: 1px solid #2d4565;
                border-radius: 16px;
            }

            QLabel#title {
                font-size: 25px;
                font-weight: 750;
                color: #f4f7fc;
            }

            QLabel#subtitle {
                font-size: 12px;
                color: #8b9bb0;
            }

            QLabel#badge {
                background: #14251f;
                color: #7ce4ad;
                border: 1px solid #2b6144;
                border-radius: 11px;
                padding: 4px 8px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            QGroupBox {
                background: #141c26;
                border: 1px solid #27384b;
                border-radius: 13px;
                margin-top: 10px;
                padding-top: 9px;
                color: #aabbd0;
                font-size: 10px;
                font-weight: 750;
                letter-spacing: 0.8px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 7px;
                background: #0d1219;
            }

            QLabel#fieldLabel {
                color: #becbda;
                font-size: 11px;
                font-weight: 650;
            }

            QComboBox, QLineEdit {
                background: #0c131d;
                border: 1px solid #2d4055;
                border-radius: 8px;
                padding: 7px 10px;
                color: #edf4ff;
                selection-background-color: #315fae;
            }

            QComboBox:hover, QLineEdit:hover {
                border-color: #426487;
            }

            QComboBox:focus, QLineEdit:focus {
                border: 1px solid #58a7ff;
            }

            QComboBox QAbstractItemView {
                background: #141c26;
                color: #edf4ff;
                border: 1px solid #344b64;
                selection-background-color: #2e5fae;
                selection-color: #ffffff;
            }

            QPushButton {
                min-height: 34px;
                padding: 0 12px;
                border-radius: 8px;
                border: 1px solid #31445a;
                background: #1b2634;
                color: #dce7f5;
                font-weight: 650;
            }

            QPushButton:hover {
                background: #24354a;
                border-color: #4a688b;
            }

            QPushButton:pressed {
                background: #172231;
            }

            QPushButton:disabled {
                color: #66798f;
                background: #151e29;
                border-color: #243244;
            }

            QPushButton#primaryButton {
                background: #286ee8;
                border: 1px solid #5194ff;
                color: #ffffff;
            }

            QPushButton#primaryButton:hover {
                background: #3a81f5;
            }

            QPushButton#primaryButton:pressed {
                background: #205bc3;
            }

            QPushButton#secondaryButton {
                background: #192432;
            }

            QCheckBox {
                color: #a9b9cc;
                spacing: 7px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #40556c;
                border-radius: 4px;
                background: #0c131d;
            }

            QCheckBox::indicator:checked {
                background: #3278ee;
                border-color: #64a3ff;
            }

            QLabel#hint {
                color: #788ca3;
                font-size: 10px;
            }

            QLabel#microBadge {
                background: #101a27;
                color: #80b9ff;
                border: 1px solid #2d4666;
                border-radius: 7px;
                padding: 4px 7px;
                font-size: 8px;
                font-weight: 750;
                letter-spacing: 0.5px;
            }

            QLabel#countBadge {
                background: #172941;
                color: #91c3ff;
                border: 1px solid #2d4e75;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 700;
            }

            QScrollArea#sequenceScroll {
                background: #0d141e;
                border: 1px solid #28394d;
                border-radius: 9px;
            }

            QWidget#sequenceStrip {
                background: #0d141e;
            }

            QLabel#noteChip {
                background: #18283e;
                color: #aacbff;
                border: 1px solid #2b4b73;
                border-radius: 8px;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 700;
            }

            QLabel#noteChipLatest {
                background: #123a50;
                color: #a5f0ff;
                border: 1px solid #39b6dc;
                border-radius: 8px;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 800;
            }

            QLabel#sequenceEmpty {
                color: #657990;
                padding-left: 5px;
                font-size: 10px;
            }

            QLabel#pipelineIcon {
                background: #162e4d;
                color: #69c9ff;
                border: 1px solid #2d5a8b;
                border-radius: 10px;
                font-size: 20px;
                font-weight: 800;
            }

            QLabel#pipelineHeading {
                color: #c6d8ed;
                font-size: 11px;
                font-weight: 650;
            }

            QProgressBar#pipelineProgress {
                background: #0b121b;
                border: 0;
                border-radius: 3px;
                max-height: 6px;
            }

            QProgressBar#pipelineProgress::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #397dff, stop:1 #5ce4f7
                );
                border-radius: 3px;
            }

            QFrame#pipelineStep {
                background: #101721;
                border: 1px solid #26374b;
                border-radius: 9px;
            }

            QFrame#pipelineStep[stepState="active"] {
                background: #142842;
                border: 1px solid #4588df;
            }

            QFrame#pipelineStep[stepState="complete"] {
                background: #10261f;
                border: 1px solid #28674f;
            }

            QLabel#stepNumber {
                background: #1b2838;
                color: #8199b5;
                border: 1px solid #2f435b;
                border-radius: 8px;
                font-size: 10px;
                font-weight: 800;
            }

            QFrame#pipelineStep[stepState="active"] QLabel#stepNumber {
                background: #1b4774;
                color: #aee4ff;
                border: 1px solid #478cd3;
            }

            QFrame#pipelineStep[stepState="complete"] QLabel#stepNumber {
                background: #194a38;
                color: #9af3c6;
                border: 1px solid #2c7658;
            }

            QLabel#stepTitle {
                color: #cbd8e8;
                font-size: 11px;
                font-weight: 700;
            }

            QLabel#stepDescription {
                color: #73869e;
                font-size: 10px;
            }

            QFrame#pipelineStep[stepState="active"] QLabel#stepTitle {
                color: #dff2ff;
            }

            QFrame#pipelineStep[stepState="complete"] QLabel#stepTitle {
                color: #a7e8ca;
            }

            QFrame#securityFrame {
                background: #101f1c;
                border: 1px solid #245441;
                border-radius: 9px;
            }

            QLabel#securityTitle {
                color: #7edbb0;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 0.7px;
            }

            QLabel#securityText {
                color: #87a898;
                font-size: 10px;
            }

            QFrame#separator {
                color: #263446;
            }

            QLabel#status {
                color: #8092a8;
                font-size: 10px;
            }

            QScrollBar:horizontal {
                height: 7px;
                background: #111a26;
                margin: 1px 4px 1px 4px;
                border-radius: 3px;
            }

            QScrollBar::handle:horizontal {
                background: #324e70;
                min-width: 26px;
                border-radius: 3px;
            }

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
            """
        )

    def refresh_devices(self) -> None:
        try:
            devices = self.capture.list_devices()
        except MidiInputError as exc:
            self._set_status(f"●  Unable to read MIDI devices: {exc}")
            return

        current_device = self.device_combo.currentText()
        self.device_combo.clear()
        self.device_combo.addItems(devices)

        if current_device in devices:
            self.device_combo.setCurrentText(current_device)

        if devices:
            self._set_status(f"●  {len(devices)} MIDI device(s) available.")
        else:
            self._set_status("●  No MIDI device detected.")

    def toggle_capture(self) -> None:
        if self.capture.is_running:
            self.capture.stop()
            self.record_button.setText("Start capture")
            self.keyboard_state_label.setText("CAPTURE PAUSED")
            self._set_status("●  Capture stopped.")
            return

        device = self.device_combo.currentText().strip()
        if not device:
            QMessageBox.warning(self, "MIDI", "Select a MIDI device.")
            return

        try:
            self.capture.start(device)
            self.record_button.setText("Stop capture")
            self.keyboard_state_label.setText("LISTENING")
            self._set_status("●  Capturing MIDI notes…")
        except MidiInputError as exc:
            QMessageBox.critical(self, "MIDI", str(exc))
            self._set_status("●  Capture error.")

    def clear_sequence(self) -> None:
        self.capture.clear()
        self.piano_keyboard.set_sequence(())
        self._clear_password()
        self._refresh_sequence()
        self.keyboard_state_label.setText(
            "LISTENING" if self.capture.is_running else "WAITING FOR INPUT"
        )
        self._set_pipeline_stage("idle")
        self._set_status("●  Musical sequence cleared.")

    def generate_password(self) -> None:
        if self._worker is not None:
            return

        length = int(self.length_combo.currentText())
        sequence = self.capture.sequence
        self._clear_password()
        self.show_checkbox.setChecked(False)

        # Freeze the input sequence before deriving so the displayed result
        # always corresponds to the exact notes shown in the UI.
        if self.capture.is_running:
            self.capture.stop()
            self.record_button.setText("Start capture")
            self.keyboard_state_label.setText("CAPTURE PAUSED")

        worker = _PasswordWorker(self.password_service, sequence, length, self)
        worker.progress.connect(self._set_pipeline_stage)
        worker.succeeded.connect(self._on_password_generated)
        worker.failed.connect(self._on_generation_failed)
        worker.finished.connect(self._on_generation_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker

        self._set_pipeline_stage("idle")
        self._set_status("●  Starting deterministic derivation…")
        self._set_generation_controls(False)
        worker.start()

    def _set_generation_controls(self, enabled: bool) -> None:
        self.device_combo.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.record_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.length_combo.setEnabled(enabled)
        self.generate_button.setEnabled(enabled)

    def _set_pipeline_stage(self, stage: str) -> None:
        if stage not in self._STAGE_INDEX and stage != "idle":
            return

        self.pipeline_heading.setText(self._STAGE_MESSAGES[stage])
        current_index = self._STAGE_INDEX.get(stage, -1)

        if stage == "idle":
            self.pipeline_progress.setValue(0)
        else:
            values = {"fingerprint": 18, "scrypt": 48, "expand": 78, "complete": 100}
            self.pipeline_progress.setValue(values[stage])

        for key, card in self._pipeline_cards.items():
            index = self._STAGE_INDEX[key]
            if stage == "complete" or (current_index >= 0 and index < current_index):
                state = "complete"
            elif index == current_index:
                state = "active"
            else:
                state = "idle"

            if card.property("stepState") != state:
                card.setProperty("stepState", state)
                card.style().unpolish(card)
                card.style().polish(card)
                card.update()

    def _on_password_generated(self, password: str) -> None:
        self.password_entry.setText(password)
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_checkbox.setChecked(False)
        self.copy_button.setEnabled(True)
        self._set_pipeline_stage("complete")
        self._set_status("●  Password generated locally and kept in memory.")

    def _on_generation_failed(self, message: str) -> None:
        self._clear_password()
        self._set_pipeline_stage("idle")
        QMessageBox.warning(self, "Password generation failed", message)
        self._set_status("●  Derivation failed. Check the sequence and try again.")

    def _on_generation_finished(self) -> None:
        self._worker = None
        self._set_generation_controls(True)

    def toggle_password_visibility(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password_entry.setEchoMode(mode)

    def copy_password(self) -> None:
        value = self.password_entry.text()
        if not value:
            return

        QApplication.clipboard().setText(value)
        self._set_status("●  Password copied to clipboard. Clear it when finished.")

    def _render_sequence(self, names: tuple[str, ...]) -> None:
        # Remove current chips from the layout before scheduling them for deletion.
        while self.sequence_strip_layout.count():
            item = self.sequence_strip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        visible_names = names[-14:]
        show_earlier = len(names) > len(visible_names)
        chip_width = 52
        chip_height = 32
        chip_spacing = self.sequence_strip_layout.spacing()
        margin_left, margin_top, margin_right, margin_bottom = (
            self.sequence_strip_layout.getContentsMargins()
        )

        if show_earlier:
            earlier = QLabel("…")
            earlier.setObjectName("noteChip")
            earlier.setAlignment(Qt.AlignmentFlag.AlignCenter)
            earlier.setFixedSize(34, chip_height)
            earlier.setToolTip(f"{len(names) - len(visible_names)} earlier notes")
            self.sequence_strip_layout.addWidget(earlier)

        for index, name in enumerate(visible_names):
            chip = QLabel(name)
            chip.setObjectName(
                "noteChipLatest" if index == len(visible_names) - 1 else "noteChip"
            )
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Fixed width prevents Qt's layout from squeezing the labels into slivers.
            chip.setFixedSize(chip_width, chip_height)
            self.sequence_strip_layout.addWidget(chip)

        if not names:
            empty = QLabel("Play a few notes to begin")
            empty.setObjectName("sequenceEmpty")
            empty.setFixedSize(190, chip_height)
            self.sequence_strip_layout.addWidget(empty)

        # Compute content width explicitly. QWidget.layout().sizeHint() may not yet
        # have been recalculated when MIDI notes arrive rapidly.
        chip_count = len(visible_names) + int(show_earlier)
        if not names:
            content_width = 190
            chip_count = 1
        else:
            content_width = len(visible_names) * chip_width
            if show_earlier:
                content_width += 34
            content_width += max(0, chip_count - 1) * chip_spacing

        content_width += margin_left + margin_right
        viewport_width = max(1, self.sequence_scroll.viewport().width())
        self.sequence_strip.setFixedWidth(max(content_width, viewport_width))
        self.sequence_strip.updateGeometry()

        self.sequence_strip_layout.addStretch(1)

        QTimer.singleShot(
            0,
            lambda: self.sequence_scroll.horizontalScrollBar().setValue(
                self.sequence_scroll.horizontalScrollBar().maximum()
            ),
        )

    def _refresh_sequence(self) -> None:
        sequence = self.capture.sequence
        if sequence.notes == self._last_sequence:
            return

        previous_count = len(self._last_sequence)
        self._last_sequence = sequence.notes
        names = sequence.display_names()

        self.piano_keyboard.set_sequence(sequence.notes)
        self._render_sequence(names)
        self.count_label.setText(f"{len(names)} notes")
        if names:
            self.keyboard_state_label.setText(
                "LISTENING" if self.capture.is_running else "NOTES CAPTURED"
            )
        elif not self.capture.is_running:
            self.keyboard_state_label.setText("WAITING FOR INPUT")

        if self._worker is None:
            if self.password_entry.text():
                self._clear_password()
                self._set_status("●  Sequence changed; generate a new password.")
            elif len(names) > previous_count:
                self._set_status(f"●  Captured {len(names)} note(s).")

            self._set_pipeline_stage("idle")

    def _clear_password(self) -> None:
        self.password_entry.clear()
        self.copy_button.setEnabled(False)

    def _set_status(self, value: str) -> None:
        self.status_label.setText(value)

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self.capture.stop()
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait()
        event.accept()
