"""Thin local administration client for the P004 v1 Local Agent Controller API."""

from .client import (
    ADMIN_OPERATIONS,
    ADMIN_REQUEST_SCHEMA,
    ADMIN_RESPONSE_SCHEMA,
    ADMIN_SOCKET_RELATIVE_PATH,
    MAX_ADMIN_MESSAGE_BYTES,
    LacctlBoundaryError,
    LacctlClient,
    LacctlError,
    LacctlProtocolError,
    LacctlRequestRejected,
    LacctlUnavailable,
    canonical_json,
    decode_response_line,
    encode_request,
    resolve_admin_socket_path,
    strict_json_loads,
)

__all__ = [
    "ADMIN_OPERATIONS",
    "ADMIN_REQUEST_SCHEMA",
    "ADMIN_RESPONSE_SCHEMA",
    "ADMIN_SOCKET_RELATIVE_PATH",
    "MAX_ADMIN_MESSAGE_BYTES",
    "LacctlBoundaryError",
    "LacctlClient",
    "LacctlError",
    "LacctlProtocolError",
    "LacctlRequestRejected",
    "LacctlUnavailable",
    "canonical_json",
    "decode_response_line",
    "encode_request",
    "resolve_admin_socket_path",
    "strict_json_loads",
]
