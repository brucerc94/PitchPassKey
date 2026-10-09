<div align="center">

<img src="assets/pitchpasskey.svg" alt="PitchPassKey logo" width="180"/>

# PitchPassKey

**Music-inspired, cross-machine deterministic password generation**

Capture notes from a MIDI controller and reproduce the same password on different computers without importing a profile or storing a machine-specific key.

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt%206-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)

</div>

## Overview

PitchPassKey is a local desktop application that turns an ordered sequence of musical notes into a deterministic password.

```text
MIDI notes → scrypt → HMAC-SHA-256 expansion → password
```

The same canonical sequence and the same requested output length produce the same output on supported computers. PitchPassKey does not generate or store a random per-installation secret.

## License

PitchPassKey is distributed under the [PolyForm Noncommercial License 1.0.0](LICENSE).

You may use, modify, and redistribute this project for permitted noncommercial purposes under the license terms. Commercial use—including selling copies or incorporating the software into a commercial product or service—is not permitted without separate permission from the copyright holder. Read the full license before using the project.

This is source-available software, not OSI-approved open-source software, because the license restricts commercial use. See the [Open Source Initiative's Open Source Definition](https://opensource.org/osd) for the distinction.

## Features

- Capture MIDI notes in order.
- See a custom piano keyboard illuminate as notes are captured.
- Review recent notes as a scrollable visual sequence.
- Watch the derivation pipeline report its actual stages while the UI remains responsive.
- Use note number and note order as the secret input.
- Ignore velocity, note duration and timing in the current version.
- Derive passwords deterministically using scrypt and HMAC-SHA-256.
- Reproduce the same output across computers without profiles, account files or key synchronization.
- Choose a password length in the UI.
- Mask generated passwords by default and copy them to the clipboard.
- Dark PySide6 / Qt 6 desktop interface.
- Clean Architecture: the core is independent from the UI and MIDI device layer.

## Portability

All algorithm parameters and the canonical encoding are fixed and versioned. The notes are the only secret input; no machine-specific key or local profile is required.

The same notes and output length reproduce the same password on every supported computer running the same algorithm version.

## Security limitations

This design prioritizes portability and memorability. Because the notes are the only secret input, anyone who learns or successfully guesses the complete sequence can reproduce the password using the public algorithm.

- Familiar songs, common scales, repeated patterns and short sequences can be guessed.
- scrypt makes each guess more expensive, but cannot add entropy that is not present in the sequence.
- The current version has no per-site field. Using the same notes and length produces the same password for every site.
- Sustain pedal state, velocity and timing are not part of the current input.
- PitchPassKey has not undergone an independent cryptographic audit and should not yet be the sole protection for high-value accounts.
- Clipboard contents may remain available until replaced or cleared.

For important accounts, use a password manager and multi-factor authentication until PitchPassKey has been independently reviewed.

## Current input format

The current version uses only MIDI note number and note order. It ignores MIDI velocity, timing, duration and sustain pedal state.

Pedal state can be added in a future version as another explicit part of the canonical input. That will require an algorithm/input-format version change, because any change to the input representation changes the generated output.

## User interface

1. **MIDI input** — select a device and start or stop capture.
2. **Live piano** — see the most recent note glow on the virtual keyboard.
3. **Musical sequence** — review the captured notes in order.
4. **Derivation engine** — follow the fingerprint, scrypt, and HMAC-SHA-256 stages.
5. **Password output** — choose a length, generate, reveal or copy the result.

The progress animation is driven by callbacks from the actual derivation steps; it does not claim that the melody is being encrypted as each note is played. The expensive derivation runs in a worker thread so the interface can remain responsive.

No profile import, secret file or account is required.

## Architecture

```text
src/pitchpasskey/
├── domain/
│   ├── models.py
│   ├── policies.py
│   └── ports.py
├── application/
│   ├── capture_sequence.py
│   └── password_service.py
├── infrastructure/
│   ├── audio/
│   ├── crypto/
│   └── midi/
└── presentation/
    └── ui.py
```

## Technology

- Python 3.10+
- PySide6 / Qt 6
- mido and python-rtmidi
- Python `hashlib.scrypt`
- HMAC-SHA-256
- pytest

## Installation

### Windows

Run:

```text
run.bat
```

The first launch creates `.venv` and installs dependencies. Later launches reuse the environment. To force a repair:

```bat
run.bat --repair
```

### Manual installation

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
python -m pip install -e .
python -m pitchpasskey
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -e .
python -m pitchpasskey
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Roadmap

- Add optional sustain-pedal state as additional secret input.
- Define test vectors for each derivation version.
- Improve MIDI device compatibility and error handling.
- Package desktop builds for end users.
- Add automated UI tests.
- Obtain independent cryptographic review.

## Project status

PitchPassKey is an early-stage project. Its current design prioritizes deterministic, cross-machine output using only the notes the user remembers.

## License reminder

The complete license is in [LICENSE](LICENSE). A public repository does not make commercial use permissible; follow the license terms or request separate permission.
