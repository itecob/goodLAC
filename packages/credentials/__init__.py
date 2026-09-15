"""Controller-only credential provider contracts."""

from .provider import SecretProvider, SecretProviderError, validate_credential_ref

__all__ = ["SecretProvider", "SecretProviderError", "validate_credential_ref"]
