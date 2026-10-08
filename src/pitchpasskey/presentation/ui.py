from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from pitchpasskey.application.capture_sequence import SequenceCapture
from pitchpasskey.application.password_service import PasswordService
from pitchpasskey.infrastructure.midi.midi_controller import MidiInputError
from pitchpasskey.infrastructure.secrets.keyring_secret_store import SecretStoreError


class MainWindow:
    """Minimal desktop presentation layer."""

    def __init__(
        self,
        root: tk.Tk,
        capture: SequenceCapture,
        password_service: PasswordService,
    ) -> None:
        self.root = root
        self.capture = capture
        self.password_service = password_service

        self._device_var = tk.StringVar()
        self._sequence_var = tk.StringVar(value="—")
        self._count_var = tk.StringVar(value="0 notas")
        self._password_var = tk.StringVar()
        self._show_password = tk.BooleanVar(value=False)
        self._length_var = tk.IntVar(value=password_service.policy.length)
        self._status_var = tk.StringVar(value="Listo")

        self._build()
        self.refresh_devices()
        self._schedule_sequence_refresh()

    def _build(self) -> None:
        self.root.title("PitchPassKey")
        self.root.geometry("720x460")
        self.root.minsize(620, 400)

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="PitchPassKey", font=("TkDefaultFont", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Secuencia MIDI → password").pack(anchor="w", pady=(2, 20))

        input_frame = ttk.LabelFrame(outer, text="Entrada MIDI", padding=14)
        input_frame.pack(fill="x")

        ttk.Label(input_frame, text="Dispositivo").grid(row=0, column=0, sticky="w")
        self.device_combo = ttk.Combobox(
            input_frame,
            textvariable=self._device_var,
            state="readonly",
            width=42,
        )
        self.device_combo.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        ttk.Button(input_frame, text="Actualizar", command=self.refresh_devices).grid(
            row=0, column=2, padx=(10, 0)
        )

        self.record_button = ttk.Button(
            input_frame,
            text="Iniciar captura",
            command=self.toggle_capture,
        )
        self.record_button.grid(row=1, column=1, sticky="w", pady=(14, 0))

        ttk.Label(
            input_frame,
            text="Solo cuenta la tecla y su orden. Velocity, timing y duración se ignoran.",
            foreground="#666666",
        ).grid(row=2, column=1, sticky="w", pady=(10, 0))

        ttk.Label(
            input_frame,
            text="Audio: preparado como fuente futura de notas.",
            foreground="#666666",
        ).grid(row=3, column=1, sticky="w", pady=(5, 0))
        input_frame.columnconfigure(1, weight=1)

        sequence_frame = ttk.LabelFrame(outer, text="Secuencia capturada", padding=14)
        sequence_frame.pack(fill="x", pady=(16, 0))

        ttk.Label(
            sequence_frame,
            textvariable=self._sequence_var,
            font=("TkFixedFont", 12),
        ).pack(anchor="w")
        ttk.Label(sequence_frame, textvariable=self._count_var).pack(anchor="w", pady=(6, 0))
        ttk.Button(sequence_frame, text="Limpiar", command=self.clear_sequence).pack(
            anchor="w", pady=(12, 0)
        )

        output_frame = ttk.LabelFrame(outer, text="Password", padding=14)
        output_frame.pack(fill="x", pady=(16, 0))

        ttk.Label(output_frame, text="Longitud").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            output_frame,
            textvariable=self._length_var,
            values=(16, 20, 24, 32, 40, 48, 64),
            state="readonly",
            width=6,
        ).grid(row=0, column=1, padx=(10, 0))

        ttk.Button(output_frame, text="Generar", command=self.generate_password).grid(
            row=1, column=0, sticky="w", pady=(14, 0)
        )

        self.password_entry = ttk.Entry(
            output_frame,
            textvariable=self._password_var,
            state="readonly",
            show="•",
        )
        self.password_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Checkbutton(
            output_frame,
            text="Mostrar",
            variable=self._show_password,
            command=self.toggle_password_visibility,
        ).grid(row=2, column=2, padx=(10, 0))

        self.copy_button = ttk.Button(
            output_frame,
            text="Copiar",
            state="disabled",
            command=self.copy_password,
        )
        self.copy_button.grid(row=3, column=0, sticky="w", pady=(10, 0))
        output_frame.columnconfigure(0, weight=1)

        ttk.Label(outer, textvariable=self._status_var).pack(anchor="w", pady=(16, 0))
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def refresh_devices(self) -> None:
        try:
            devices = self.capture.list_devices()
        except MidiInputError as exc:
            self._set_status(f"No se pudieron leer los dispositivos MIDI: {exc}")
            return

        self.device_combo["values"] = devices
        if devices:
            if self._device_var.get() not in devices:
                self._device_var.set(devices[0])
            self._set_status(f"{len(devices)} dispositivo(s) MIDI disponible(s).")
        else:
            self._device_var.set("")
            self._set_status("No se detectó un dispositivo MIDI.")

    def toggle_capture(self) -> None:
        if self.capture.is_running:
            self.capture.stop()
            self.record_button.configure(text="Iniciar captura")
            self._set_status("Captura detenida.")
            return

        device = self._device_var.get().strip()
        if not device:
            messagebox.showwarning("MIDI", "Selecciona un dispositivo MIDI.")
            return

        try:
            self.capture.start(device)
            self.record_button.configure(text="Detener captura")
            self._set_status("Capturando…")
        except MidiInputError as exc:
            messagebox.showerror("MIDI", str(exc))
            self._set_status("Error de captura.")

    def clear_sequence(self) -> None:
        self.capture.clear()
        self._password_var.set("")
        self.copy_button.configure(state="disabled")
        self._set_status("Secuencia limpiada.")

    def generate_password(self) -> None:
        try:
            password = self.password_service.generate(
                self.capture.sequence,
                int(self._length_var.get()),
            )
            self._password_var.set(password)
            self.copy_button.configure(state="normal")
            self._set_status("Password generado y mantenido solo en memoria.")
        except (ValueError, SecretStoreError) as exc:
            messagebox.showwarning("No se pudo generar", str(exc))

    def toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self._show_password.get() else "•")

    def copy_password(self) -> None:
        value = self._password_var.get()
        if not value:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()
        self._set_status("Password copiado al portapapeles. Límpialo al terminar.")

    def _schedule_sequence_refresh(self) -> None:
        sequence = self.capture.sequence
        names = sequence.display_names()
        self._sequence_var.set(" → ".join(names[-24:]) if names else "—")
        suffix = "…" if len(names) > 24 else ""
        self._count_var.set(f"{len(names)} notas{suffix}")
        if self.root.winfo_exists():
            self.root.after(100, self._schedule_sequence_refresh)

    def _set_status(self, value: str) -> None:
        self._status_var.set(value)

    def close(self) -> None:
        self.capture.stop()
        self.root.destroy()
