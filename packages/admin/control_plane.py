from __future__ import annotations

import os
import signal
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from packages.lacctl import LacctlClient, LacctlError

CONTROL_PLANE_STATUS_SCHEMA = "lac.admin-control-plane-status/v1"
CONTROL_PLANE_READY_SCHEMA = "lac.admin-control-plane-ready/v1"


class AdminControlPlaneError(RuntimeError):
    """Shared administrator/control-plane service is unavailable or cross-bound."""


@dataclass(frozen=True)
class AdminControlPlaneLease:
    state_path: Path
    state_dev: int
    state_ino: int
    server_pid: int
    started_pid: int | None

    @property
    def started_here(self) -> bool:
        return self.started_pid is not None


def _canonical_state(path: str | os.PathLike[str]) -> tuple[Path, os.stat_result]:
    candidate = Path(path).expanduser()
    try:
        info = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise AdminControlPlaneError("canonical controller state is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise AdminControlPlaneError("canonical controller state must be a real regular file")
    resolved_info = resolved.stat()
    if resolved_info.st_uid != os.getuid():
        raise AdminControlPlaneError("canonical controller state has unexpected owner UID")
    return resolved, resolved_info


def _validate_status(value: Any, state: Path, info: os.stat_result) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdminControlPlaneError("administrator control-plane status is malformed")
    status = dict(value)
    required = {"schema", "owner_uid", "pid", "state_path", "state_dev", "state_ino"}
    if set(status) != required or status.get("schema") != CONTROL_PLANE_STATUS_SCHEMA:
        raise AdminControlPlaneError("administrator control-plane status fields are invalid")
    if status.get("owner_uid") != os.getuid():
        raise AdminControlPlaneError("administrator control-plane owner UID mismatch")
    if not isinstance(status.get("pid"), int) or isinstance(status.get("pid"), bool) or status["pid"] <= 1:
        raise AdminControlPlaneError("administrator control-plane PID is invalid")
    if status.get("state_path") != str(state):
        raise AdminControlPlaneError("administrator endpoint is bound to a different canonical controller state")
    if status.get("state_dev") != info.st_dev or status.get("state_ino") != info.st_ino:
        raise AdminControlPlaneError("administrator endpoint canonical-state identity mismatch")
    return status


def probe_admin_control_plane(state: str | os.PathLike[str]) -> dict[str, Any]:
    canonical, info = _canonical_state(state)
    try:
        value = LacctlClient().call("controller.status", {})
    except LacctlError as exc:
        raise AdminControlPlaneError(str(exc)) from exc
    return _validate_status(value, canonical, info)


def ensure_admin_control_plane(
    state: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str] | None = None,
    timeout: float = 8.0,
) -> AdminControlPlaneLease:
    canonical, info = _canonical_state(state)
    try:
        status = probe_admin_control_plane(canonical)
        return AdminControlPlaneLease(
            state_path=canonical,
            state_dev=info.st_dev,
            state_ino=info.st_ino,
            server_pid=status["pid"],
            started_pid=None,
        )
    except AdminControlPlaneError:
        pass

    root = Path(repo_root).resolve(strict=True) if repo_root is not None else Path(__file__).resolve().parents[2]
    server_script = root / "scripts" / "lac-admin-server"
    if not server_script.is_file() or server_script.is_symlink():
        raise AdminControlPlaneError("trusted administrator server script is unavailable")

    argv = [sys.executable, "-u", str(server_script), "--state", str(canonical)]
    devnull = os.open(os.devnull, os.O_RDWR)
    try:
        file_actions = [
            (os.POSIX_SPAWN_DUP2, devnull, 0),
            (os.POSIX_SPAWN_DUP2, devnull, 1),
            (os.POSIX_SPAWN_DUP2, devnull, 2),
        ]
        spawned_pid = os.posix_spawn(
            sys.executable,
            argv,
            os.environ.copy(),
            file_actions=file_actions,
            setsid=True,
        )
    except (AttributeError, OSError) as exc:
        raise AdminControlPlaneError("shared administrator control plane could not be spawned") from exc
    finally:
        os.close(devnull)

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status = probe_admin_control_plane(canonical)
            if status["pid"] == spawned_pid:
                return AdminControlPlaneLease(
                    state_path=canonical,
                    state_dev=info.st_dev,
                    state_ino=info.st_ino,
                    server_pid=spawned_pid,
                    started_pid=spawned_pid,
                )
            # A concurrent legitimate same-state starter won. Never stop or unlink it.
            try:
                os.kill(spawned_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(spawned_pid, 0)
            except ChildProcessError:
                pass
            return AdminControlPlaneLease(
                state_path=canonical,
                state_dev=info.st_dev,
                state_ino=info.st_ino,
                server_pid=status["pid"],
                started_pid=None,
            )
        except AdminControlPlaneError as exc:
            last_error = exc
        try:
            waited, _status = os.waitpid(spawned_pid, os.WNOHANG)
        except ChildProcessError:
            waited = spawned_pid
        if waited == spawned_pid:
            # A bind loser may have exited while a concurrent same-state winner is
            # finishing startup. Keep probing until the bounded deadline.
            time.sleep(0.05)
            continue
        time.sleep(0.05)

    try:
        os.kill(spawned_pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        os.waitpid(spawned_pid, 0)
    except ChildProcessError:
        pass
    try:
        status = probe_admin_control_plane(canonical)
        return AdminControlPlaneLease(
            state_path=canonical,
            state_dev=info.st_dev,
            state_ino=info.st_ino,
            server_pid=status["pid"],
            started_pid=None,
        )
    except AdminControlPlaneError as exc:
        raise AdminControlPlaneError(
            f"shared administrator control plane failed to become ready: {last_error or exc}"
        ) from exc


def stop_owned_admin_control_plane(lease: AdminControlPlaneLease, *, timeout: float = 5.0) -> bool:
    """Qualification cleanup for a service started by this exact lease.

    Production Pi sessions intentionally do not call this. Cleanup never unlinks the socket.
    """
    if not isinstance(lease, AdminControlPlaneLease) or lease.started_pid is None:
        return False
    try:
        status = probe_admin_control_plane(lease.state_path)
    except AdminControlPlaneError:
        return False
    if (
        status.get("pid") != lease.started_pid
        or status.get("state_dev") != lease.state_dev
        or status.get("state_ino") != lease.state_ino
    ):
        return False
    try:
        os.kill(lease.started_pid, signal.SIGTERM)
    except ProcessLookupError:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            waited, _status = os.waitpid(lease.started_pid, os.WNOHANG)
            if waited == lease.started_pid:
                return True
        except ChildProcessError:
            pass
        try:
            os.kill(lease.started_pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False
