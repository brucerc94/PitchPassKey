# PitchPassKey

Local Python desktop app that derives password output from an ordered sequence of notes received from a MIDI controller.

## Design

- Clean Architecture and SOLID boundaries.
- Domain knows nothing about MIDI, audio, UI, or the OS.
- Current input: MIDI controller.
- Future input: audio transcription through the same `NoteInputSource` boundary.
- Only note number and order matter. Velocity, timing, duration, sustain, and other performance data are ignored.
- Per-profile secret is stored using the operating system keyring.
- Password output is masked by default in the UI.

```
MIDI Controller -> NoteInputSource -> NoteSequence -> PasswordService
                                      -> PasswordDeriver -> Password
Audio Transcriber (future) ----------^
```

## Security model

The note sequence is secret input, not a cryptographic key by itself. A per-profile 32-byte secret is generated once and stored in the OS credential store. HMAC-SHA-256 derives deterministic output from that secret, an optional context, and the canonical note sequence.

This means the same sequence and context on the same profile reproduce the same password, while a copied sequence alone does not reproduce it on another machine. A future portable profile/key export can be added behind the secret-store interface without changing the core.

Avoid predictable public melodies for high-value secrets. For critical accounts, a password manager and MFA remain preferable.

## Run

Python 3.10+.

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -e .
python -m pitchpasskey
```

Linux/macOS activation: `source .venv/bin/activate`.

Development checks:

```bash
python -m pytest
```

## Future audio integration

The audio project should only need an adapter that emits normalized `NoteEvent(midi_note=...)` objects. The domain, password engine, and UI do not need to know whether the note came from MIDI hardware or audio transcription.
