from __future__ import annotations

import secrets

import keyring
from keyring.errors import KeyringError


class SecretStoreError(RuntimeError):
    """Raised when an OS-backed secret store cannot be accessed."""


class KeyringSecretStore:
    """Persist profile secrets in the operating system credential store."""

    _SERVICE = "PitchPassKey"
    _USERNAME = "profile-key"

    def get_or_create(self, profile: str) -> bytes:
        service = f"{self._SERVICE}/{profile}"

        try:
            encoded = keyring.get_password(service, self._USERNAME)
            if encoded:
                secret = bytes.fromhex(encoded)
                if len(secret) != 32:
                    raise ValueError("invalid stored secret length")
                return secret

            secret = secrets.token_bytes(32)
            keyring.set_password(service, self._USERNAME, secret.hex())
            return secret
        except (KeyringError, ValueError, TypeError) as exc:
            raise SecretStoreError(
                "The OS keyring is unavailable. PitchPassKey never writes the profile secret "
                "to a plaintext application file."
            ) from exc
