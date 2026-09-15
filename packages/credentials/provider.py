from __future__ import annotations

from typing import Protocol, runtime_checkable


class SecretProviderError(RuntimeError):
    """Secret-provider boundary failed closed without exposing secret material."""


def validate_credential_ref(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SecretProviderError("credential_ref must be a non-empty trimmed string")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise SecretProviderError("credential_ref contains a control character")
    return value


@runtime_checkable
class SecretProvider(Protocol):
    """Controller-only credential resolver.

    The returned value is deliberately opaque to LAC's agent/model-facing surface.
    Effect adapters may pass it only to deterministic service clients/factories and
    must never serialize, log, audit, or return it.
    """

    def resolve(self, credential_ref: str) -> object:
        ...
