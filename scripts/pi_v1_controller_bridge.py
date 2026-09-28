#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.adapters.pi.production import (
    PI_V1_AGENT_ID,
    PI_V1_PRINCIPAL_ID,
    PiPermissionRuntime,
    canonical_project_root,
    pi_v1_capability_manifest,
    pi_v1_project_application_id,
)
from packages.capabilities import PendingPermissionRepository
from packages.admin import AdminRequest, AdminService
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.runtime.workflow_continuation import NativeWorkflowContinuationStore
from packages.state import (
    AgentIdentityRepository,
    EmergencyPauseRepository,
    SQLiteStateStore,
)


def canonical_binary(name):
    expected = Path("/usr/bin") / name
    if not expected.is_file() or expected.is_symlink():
        found = shutil.which(name)
        if not found:
            raise RuntimeError(f"required H003 executable unavailable: {name}")
        expected = Path(found).resolve(strict=True)
        if (
            expected.parent != Path("/usr/bin")
            or expected.name != name
            or expected.is_symlink()
        ):
            raise RuntimeError(
                f"required H003 executable is not canonical /usr/bin/{name}"
            )
    return expected


def initialize_state(state, workspace):
    workspace = canonical_project_root(workspace)
    state = state.expanduser().resolve()
    is_new = not state.exists()
    store = SQLiteStateStore(state)
    try:
        if is_new:
            EmergencyPauseRepository(store).resume()
        AgentIdentityRepository(store).register_active(
            PI_V1_AGENT_ID, PI_V1_PRINCIPAL_ID
        )
        application_id = pi_v1_project_application_id(workspace)
        AdminService(store, owner_uid=os.getuid()).execute(
            AdminRequest.create(
                request_id=f"admin:pi-v1:bootstrap-register:{application_id.rsplit('.',1)[-1]}",
                operation="skills.register",
                arguments={"manifest": pi_v1_capability_manifest(application_id)},
            ),
            peer_uid=os.getuid(),
        )
    finally:
        store.close()


def build_runtime(state, workspace, run_id):
    workspace = canonical_project_root(workspace)
    application_id = pi_v1_project_application_id(workspace)
    store = SQLiteStateStore(state)
    fs = FilesystemEffectAdapter(workspace)
    shell = ShellEffectAdapter(
        workspace,
        allowed_executables=(
            canonical_binary("ls"),
            canonical_binary("cat"),
            canonical_binary("printf"),
        ),
    )
    return store, PiPermissionRuntime(
        store=store, filesystem_adapter=fs, shell_adapter=shell, run_id=run_id,
        application_id=application_id,
    )


def _continuation_application_id(store, status):
    pending_id = status.get("pending_id") if isinstance(status, dict) else None
    if not isinstance(pending_id, str) or not pending_id:
        raise RuntimeError("workflow continuation lacks pending project binding")
    matches = [
        item for item in PendingPermissionRepository(store).list_pending()
        if item.get("pending_id") == pending_id
    ]
    if len(matches) != 1:
        raise RuntimeError("workflow continuation pending project binding is unavailable or non-unique")
    application_id = matches[0].get("application_id")
    if not isinstance(application_id, str) or not application_id:
        raise RuntimeError("workflow continuation pending project application is invalid")
    return application_id


def _assert_continuation_project(store, status, application_id):
    if _continuation_application_id(store, status) != application_id:
        raise RuntimeError("workflow continuation belongs to a different governed project")


def _emit_error(exc, *, request_id=None):
    print(
        json.dumps(
            {
                "ok": False,
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            sort_keys=True,
        )
    )


def cmd_init(args):
    state = Path(args.state).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve(strict=True)
    initialize_state(state, workspace)
    print(
        json.dumps(
            {"ok": True, "state": str(state), "workspace": str(workspace)},
            sort_keys=True,
        )
    )
    return 0


def cmd_effect(args):
    state = Path(args.state).expanduser().resolve(strict=True)
    workspace = Path(args.workspace).expanduser().resolve(strict=True)
    payload = json.load(sys.stdin)
    store, runtime = build_runtime(state, workspace, args.run_id)
    request_id = None
    try:
        if isinstance(payload, dict):
            try:
                request_id = runtime.build_material(
                    tool_name=payload.get("toolName"),
                    arguments=payload.get("arguments"),
                    tool_call_id=payload.get("toolCallId"),
                )["request_id"]
            except Exception:
                pass
        result = runtime.submit_message(payload)
        request_id = result.get("request_id", request_id)
        print(
            json.dumps(
                {"ok": True, "request_id": request_id, "result": result},
                sort_keys=True,
            )
        )
    except BaseException as exc:
        _emit_error(exc, request_id=request_id)
    finally:
        store.close()
    return 0


def cmd_continuation_list(args):
    state = Path(args.state).expanduser().resolve(strict=True)
    workspace = canonical_project_root(args.workspace)
    application_id = pi_v1_project_application_id(workspace)
    store = SQLiteStateStore(state)
    try:
        raw_items = NativeWorkflowContinuationStore(store).list_status(
            recoverable_only=args.recoverable_only
        )
        items = [
            item for item in raw_items
            if _continuation_application_id(store, item) == application_id
        ]
        print(json.dumps({"ok": True, "continuations": items}, sort_keys=True))
    except BaseException as exc:
        _emit_error(exc)
    finally:
        store.close()
    return 0


def cmd_continuation_status(args):
    state = Path(args.state).expanduser().resolve(strict=True)
    workspace = canonical_project_root(args.workspace)
    application_id = pi_v1_project_application_id(workspace)
    store = SQLiteStateStore(state)
    try:
        status = NativeWorkflowContinuationStore(store).status(args.continuation_id)
        _assert_continuation_project(store, status, application_id)
        print(json.dumps({"ok": True, "continuation": status}, sort_keys=True))
    except BaseException as exc:
        _emit_error(exc)
    finally:
        store.close()
    return 0


def cmd_continuation_resume(args):
    state = Path(args.state).expanduser().resolve(strict=True)
    workspace = Path(args.workspace).expanduser().resolve(strict=True)
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict) or set(payload) - {"expected_message"}:
        raise RuntimeError("continuation resume input must contain only optional expected_message")
    expected_message = payload.get("expected_message")
    store, runtime = build_runtime(state, workspace, args.run_id)
    try:
        status = runtime.continuation_status(args.continuation_id)
        _assert_continuation_project(store, status, runtime.application_id)
        outcome = runtime.resume_continuation(
            args.continuation_id,
            expected_message=expected_message,
        )
        print(json.dumps({"ok": True, "resume": outcome}, sort_keys=True))
    except BaseException as exc:
        _emit_error(exc)
    finally:
        store.close()
    return 0


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("init")
    q.add_argument("--state", required=True)
    q.add_argument("--workspace", required=True)
    q.set_defaults(func=cmd_init)

    q = sub.add_parser("effect")
    q.add_argument("--state", required=True)
    q.add_argument("--workspace", required=True)
    q.add_argument("--run-id", required=True)
    q.set_defaults(func=cmd_effect)

    q = sub.add_parser("continuation-list")
    q.add_argument("--state", required=True)
    q.add_argument("--workspace", required=True)
    q.add_argument("--recoverable-only", action="store_true")
    q.set_defaults(func=cmd_continuation_list)

    q = sub.add_parser("continuation-status")
    q.add_argument("--state", required=True)
    q.add_argument("--workspace", required=True)
    q.add_argument("continuation_id")
    q.set_defaults(func=cmd_continuation_status)

    q = sub.add_parser("continuation-resume")
    q.add_argument("--state", required=True)
    q.add_argument("--workspace", required=True)
    q.add_argument("--run-id", required=True)
    q.add_argument("continuation_id")
    q.set_defaults(func=cmd_continuation_resume)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
