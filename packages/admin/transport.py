from __future__ import annotations

import errno
import os
import socket
import stat
import struct
from pathlib import Path
from typing import Any

from .protocol import (
    MAX_ADMIN_MESSAGE_BYTES,
    AdminProtocolError,
    decode_request_line,
    encode_response,
    error_response,
    success_response,
)
from .service import AdminService, AdminServiceError


ADMIN_SOCKET_RELATIVE_PATH = Path("lac") / "admin-v1.sock"


class AdminTransportError(RuntimeError):
    """The local owner-only administration transport could not be secured or served."""


def _require_owner_private_directory(path: Path, *, owner_uid: int) -> Path:
    if not path.is_absolute():
        raise AdminTransportError("administrator runtime directory must be absolute")
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise AdminTransportError(f"administrator runtime directory is missing: {path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise AdminTransportError("administrator runtime directory must be a real directory")
    if info.st_uid != owner_uid:
        raise AdminTransportError("administrator runtime directory is not owned by controller owner UID")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise AdminTransportError("administrator runtime directory must not grant group/other permissions")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise AdminTransportError("administrator runtime directory must be canonical and non-symlinked")
    return path


def resolve_owner_runtime_dir(*, owner_uid: int | None = None) -> Path:
    uid = os.getuid() if owner_uid is None else owner_uid
    if uid != os.getuid():
        raise AdminTransportError("production administrator runtime must use the current owner UID")
    raw = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"
    path = Path(raw)
    return _require_owner_private_directory(path, owner_uid=uid)


def default_admin_socket_path(*, owner_uid: int | None = None) -> Path:
    uid = os.getuid() if owner_uid is None else owner_uid
    return resolve_owner_runtime_dir(owner_uid=uid) / ADMIN_SOCKET_RELATIVE_PATH


class UnixAdminServer:
    """Single-owner Linux Unix-domain administration server.

    Peer credentials are checked with SO_PEERCRED before any request bytes are parsed.
    The socket exists only beneath the validated owner runtime directory and is mode 0600.
    """

    def __init__(
        self,
        service: AdminService,
        *,
        runtime_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        if not isinstance(service, AdminService):
            raise AdminTransportError("service must be an AdminService")
        if not hasattr(socket, "SO_PEERCRED"):
            raise AdminTransportError("Linux SO_PEERCRED is required for the v0.1 administrator boundary")
        self.service = service
        self.owner_uid = service.owner_uid
        self.runtime_dir = (
            resolve_owner_runtime_dir(owner_uid=self.owner_uid)
            if runtime_dir is None
            else _require_owner_private_directory(Path(runtime_dir), owner_uid=self.owner_uid)
        )
        self.socket_path = self.runtime_dir / ADMIN_SOCKET_RELATIVE_PATH
        self._listener: socket.socket | None = None
        self._socket_identity: tuple[int, int] | None = None

    def _prepare_parent(self) -> None:
        parent = self.socket_path.parent
        if not parent.exists():
            parent.mkdir(mode=0o700)
        _require_owner_private_directory(parent, owner_uid=self.owner_uid)
        try:
            parent.chmod(0o700)
        except OSError as exc:
            raise AdminTransportError("failed to harden administrator socket directory") from exc

    def _remove_stale_socket(self) -> None:
        try:
            info = self.socket_path.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISSOCK(info.st_mode):
            raise AdminTransportError("administrator socket path exists and is not a real Unix socket")
        if info.st_uid != self.owner_uid:
            raise AdminTransportError("existing administrator socket has unexpected owner UID")
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.1)
        try:
            probe.connect(str(self.socket_path))
        except OSError as exc:
            if exc.errno not in {errno.ECONNREFUSED, errno.ENOENT}:
                raise AdminTransportError("existing administrator socket cannot be safely classified") from exc
        else:
            raise AdminTransportError("administrator socket is already active")
        finally:
            probe.close()
        try:
            self.socket_path.unlink()
        except OSError as exc:
            raise AdminTransportError("failed to remove stale owner administrator socket") from exc

    def start(self) -> Path:
        if self._listener is not None:
            return self.socket_path
        self._prepare_parent()
        self._remove_stale_socket()
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        socket_identity: tuple[int, int] | None = None
        try:
            old_umask = os.umask(0o077)
            try:
                listener.bind(str(self.socket_path))
            finally:
                os.umask(old_umask)
            info = self.socket_path.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != self.owner_uid
            ):
                raise AdminTransportError("administrator socket ownership/permissions failed closed")
            # bind() success is the acquisition event. Record the exact pathname
            # identity before any later setup step can fail. A bind() failure leaves
            # this unset and therefore grants no cleanup authority.
            socket_identity = (info.st_dev, info.st_ino)
            os.chmod(self.socket_path, 0o600)
            info = self.socket_path.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != self.owner_uid
                or stat.S_IMODE(info.st_mode) != 0o600
                or (info.st_dev, info.st_ino) != socket_identity
            ):
                raise AdminTransportError("administrator socket ownership/permissions failed closed")
            listener.listen(8)
        except BaseException:
            listener.close()
            if socket_identity is not None:
                try:
                    info = self.socket_path.lstat()
                except FileNotFoundError:
                    pass
                else:
                    if (
                        stat.S_ISSOCK(info.st_mode)
                        and info.st_uid == self.owner_uid
                        and (info.st_dev, info.st_ino) == socket_identity
                    ):
                        self.socket_path.unlink()
            raise
        self._listener = listener
        self._socket_identity = socket_identity
        return self.socket_path

    @staticmethod
    def _peer_identity(connection: socket.socket) -> tuple[int, int, int]:
        credentials = connection.getsockopt(
            socket.SOL_SOCKET,
            socket.SO_PEERCRED,
            struct.calcsize("3i"),
        )
        pid, uid, gid = struct.unpack("3i", credentials)
        if pid <= 0 or uid < 0 or gid < 0:
            raise AdminTransportError("administrator peer credentials are invalid")
        return pid, uid, gid

    @staticmethod
    def _receive_one_line(connection: socket.socket) -> bytes:
        data = bytearray()
        while True:
            chunk = connection.recv(min(65536, MAX_ADMIN_MESSAGE_BYTES + 1 - len(data)))
            if not chunk:
                raise AdminProtocolError("administrator connection closed before newline")
            data.extend(chunk)
            if len(data) > MAX_ADMIN_MESSAGE_BYTES:
                raise AdminProtocolError("administrator request exceeds maximum size")
            if b"\n" in chunk or b"\n" in data:
                break
        first, separator, trailing = bytes(data).partition(b"\n")
        if not separator:
            raise AdminProtocolError("administrator request framing requires newline")
        if trailing.strip():
            raise AdminProtocolError("administrator connection may contain only one request")
        return first + b"\n"

    def serve_once(self, *, timeout: float | None = None) -> bool:
        listener = self._listener
        if listener is None:
            self.start()
            listener = self._listener
        assert listener is not None
        listener.settimeout(timeout)
        try:
            connection, _ = listener.accept()
        except socket.timeout:
            return False
        with connection:
            connection.settimeout(2.0)
            _pid, peer_uid, _gid = self._peer_identity(connection)
            # Critical ordering: reject wrong UID before reading or parsing request bytes.
            if peer_uid != self.owner_uid:
                return True
            request_id = "invalid-request"
            try:
                request = decode_request_line(self._receive_one_line(connection))
                request_id = request.request_id
                result = self.service.execute(request, peer_uid=peer_uid)
                response = success_response(request.request_id, result)
            except AdminServiceError as exc:
                response = error_response(request_id, code=exc.code, message=str(exc))
            except AdminProtocolError as exc:
                response = error_response(request_id, code="ADMIN_PROTOCOL_ERROR", message=str(exc))
            except Exception:
                # Do not reflect raw internal exceptions over the administration transport.
                response = error_response(
                    request_id,
                    code="ADMIN_INTERNAL_FAILURE",
                    message="administrator operation failed closed",
                )
            try:
                connection.sendall(encode_response(response))
            except OSError as exc:
                if exc.errno not in {errno.EPIPE, errno.ECONNRESET, errno.ENOTCONN}:
                    raise
        return True

    def serve_forever(self) -> None:
        self.start()
        try:
            while True:
                self.serve_once(timeout=1.0)
        finally:
            self.close()

    def close(self) -> None:
        listener = self._listener
        socket_identity = self._socket_identity
        self._listener = None
        self._socket_identity = None
        if listener is not None:
            listener.close()
        if socket_identity is None:
            return
        try:
            info = self.socket_path.lstat()
        except FileNotFoundError:
            return
        if (
            stat.S_ISSOCK(info.st_mode)
            and info.st_uid == self.owner_uid
            and (info.st_dev, info.st_ino) == socket_identity
        ):
            self.socket_path.unlink()
