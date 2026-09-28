#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.admin import ensure_admin_control_plane
from packages.adapters.pi.production import pi_v1_project_application_id
from scripts.pi_v1_controller_bridge import initialize_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compatibility shim: bootstrap a governed Pi project and attach to the shared goodLAC admin control plane"
    )
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--parent-pid", type=int)
    args = parser.parse_args()

    state = args.state.expanduser().resolve()
    workspace = args.workspace.expanduser().resolve(strict=True)
    initialize_state(state, workspace)
    lease = ensure_admin_control_plane(state, repo_root=REPO_ROOT)
    print(
        json.dumps(
            {
                "schema": "lac.pi-v1-admin-ready/v1",
                "pid": os.getpid(),
                "shared_control_plane_pid": lease.server_pid,
                "state": str(lease.state_path),
                "registered_application_id": pi_v1_project_application_id(workspace),
                "shared": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
