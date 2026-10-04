# ADR-004 — Linux Sandbox Backend

**Status:** Accepted for Phase 2 H001  
**Decision:** `bubblewrap`  
**Evidence:** historical sandbox qualification evidence is retained privately by ITECOB Inc.

## Context

The controlling specification requires an established Linux sandbox that constrains mounted filesystem visibility, writable paths, process authority, outbound network authority, inherited environment, credential exposure, and child-process lifetime. Tool policy alone is not an ambient-authority boundary. H001 therefore qualified both rootless Podman and bubblewrap on the actual target host rather than relying on documentation claims.

## Decision

Select `bubblewrap` for the initial `SandboxBackend` implementation because it passed every required H001 isolation probe on the target host. The qualification procedure also probed the other required candidate and recorded its exact local disposition.

Selection rule was deterministic: prefer bubblewrap when both candidates pass because it is the smaller direct namespace wrapper with no OCI image/storage lifecycle; otherwise select passing rootless Podman. If neither passes, H001 fails closed and no backend is selected.

## Binding properties

The selected backend is usable only through `packages.sandbox` and passing qualification evidence. H001 exposes no host-network mode, does not inherit the agent environment, mounts the runtime root read-only, requires explicit mounts for additional visibility, and uses established namespace/container lifecycle controls for child containment. Unknown network authority or malformed mount/runtime state fails closed.

This ADR does not authorize filesystem or shell effects by itself and does not replace the Phase 1 policy/approval/lease/dispatcher authority path.

## Alternatives

* `bubblewrap` — qualified and dispositioned in H001 evidence.
* `rootless_podman` — qualified and dispositioned in H001 evidence.
* custom sandbox — rejected by the controlling specification.

## Requalification

A backend binary replacement, material kernel/user-namespace behavior change, or future requirement for broader network authority requires deterministic requalification before relying on the changed boundary.
