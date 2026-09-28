"""Isolated owner-only Local Agent Controller administration surface."""


from .control_plane import (
    CONTROL_PLANE_READY_SCHEMA,
    CONTROL_PLANE_STATUS_SCHEMA,
    AdminControlPlaneError,
    AdminControlPlaneLease,
    ensure_admin_control_plane,
    probe_admin_control_plane,
    stop_owned_admin_control_plane,
)

from .owner_permissions import (
    OWNER_PERMISSION_CHOICES,
    OWNER_PERMISSION_DECISION_SCHEMA,
    OWNER_PERMISSION_SCOPES,
    OwnerPermissionDecisionConflict,
    OwnerPermissionDecisionError,
    OwnerPermissionDecisionService,
)
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
    "CONTROL_PLANE_READY_SCHEMA",
    "CONTROL_PLANE_STATUS_SCHEMA",
    "AdminControlPlaneError",
    "AdminControlPlaneLease",
    "ensure_admin_control_plane",
    "probe_admin_control_plane",
    "stop_owned_admin_control_plane",
    "OWNER_PERMISSION_CHOICES",
    "OWNER_PERMISSION_DECISION_SCHEMA",
    "OWNER_PERMISSION_SCOPES",
    "OwnerPermissionDecisionConflict",
    "OwnerPermissionDecisionError",
    "OwnerPermissionDecisionService",
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
