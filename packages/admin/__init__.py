"""Isolated owner-only Local Agent Controller administration surface."""

from .pending import (
    PENDING_ADMIN_RESOLUTION_SCHEMA,
    PendingAdminError,
    PendingAdminRepository,
    PendingAdminResolution,
)
from .protocol import (
    ADMIN_OPERATIONS,
    ADMIN_REQUEST_SCHEMA,
    ADMIN_RESPONSE_SCHEMA,
    MAX_ADMIN_MESSAGE_BYTES,
    AdminProtocolError,
    AdminRequest,
    decode_request_line,
    encode_response,
)
from .service import (
    AdminBadRequest,
    AdminConflict,
    AdminNotFound,
    AdminService,
    AdminServiceError,
    AdminUnauthorized,
)
from .transport import (
    ADMIN_SOCKET_RELATIVE_PATH,
    AdminTransportError,
    UnixAdminServer,
    default_admin_socket_path,
    resolve_owner_runtime_dir,
)

__all__ = [
    "PENDING_ADMIN_RESOLUTION_SCHEMA",
    "PendingAdminError",
    "PendingAdminRepository",
    "PendingAdminResolution",
    "ADMIN_OPERATIONS",
    "ADMIN_REQUEST_SCHEMA",
    "ADMIN_RESPONSE_SCHEMA",
    "MAX_ADMIN_MESSAGE_BYTES",
    "AdminProtocolError",
    "AdminRequest",
    "decode_request_line",
    "encode_response",
    "AdminBadRequest",
    "AdminConflict",
    "AdminNotFound",
    "AdminService",
    "AdminServiceError",
    "AdminUnauthorized",
    "ADMIN_SOCKET_RELATIVE_PATH",
    "AdminTransportError",
    "UnixAdminServer",
    "default_admin_socket_path",
    "resolve_owner_runtime_dir",
]
