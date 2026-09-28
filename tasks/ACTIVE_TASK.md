# ACTIVE TASK — POSTV1 R5-R001 MULTI-PI ADMIN CONTROL PLANE

## Task ID
`POSTV1-R5-R001-MULTI-PI-ADMIN-CONTROL-PLANE`

## Mode
`BLOCKER_REMEDIATION_IMPLEMENTATION`

## Trigger
R5 integrated owner UAT reached the first installed governed Pi scenario only after all retained
regression, candidate build/install, static doctor, dynamic doctor, exact Pi pin, exact FreeToken
pin, and external FreeToken readiness checks passed.

The first ordinary governed Pi launch then failed before any owner permission choice was made:

`AdminTransportError: administrator socket is already active`

Retained R5 diagnostics proved that the R5 qualification harness had already launched
`scripts/lac-admin-server` on the same `$XDG_RUNTIME_DIR/lac/admin-v1.sock` through
`policy_json="$(admin_json permissions list)"`. Because `admin_json` called `admin_start` inside
Bash command substitution, `ADMIN_PID` was assigned only in the subshell and the live owner
administrator process survived without a parent-shell PID handle.

Separately, an ordinary installed governed `pi` launch also failed on an already-active
administrator socket. Source inspection confirms each native Pi host starts its own
`pi_v1_admin_server.py`, while both that server and `scripts/lac-admin-server` instantiate the
same fixed `UnixAdminServer` endpoint.

## Product requirement
goodLAC must support multiple simultaneous governed Pi sessions on one machine/server, subject
to actual host/model-runtime capacity rather than an artificial one-Pi-per-machine controller
limit.

A solution that merely assigns arbitrary independent administrator authority domains to each Pi
session is insufficient. Preserve one canonical controller truth and exact project/application
binding.

## Required remediation outcomes
1. Fix the R5 harness lifecycle defect so temporary administrator processes cannot be orphaned by
   command substitution and qualification failure leaves no live owned admin process/socket.
2. Remove per-Pi competition for the singleton owner administrator socket.
3. Support at least two simultaneously running governed Pi sessions against the same canonical
   controller state and owner administration plane.
4. Preserve project-derived application identity and prevent Project A policy, approval,
   continuation, or owner challenge from authorizing Project B.
5. Preserve exact approval binding, deny precedence, policy re-evaluation, emergency pause,
   durable continuation/restart recovery, idempotency, receipts, and the four-tool model surface.
6. Preserve the rule that the model/sandbox cannot access or mutate the owner administrator
   surface.
7. A Pi session ending/crashing must not terminate another Pi session or invalidate the shared
   controller/admin plane.
8. Emergency pause must block consequential dispatch across concurrently running governed Pi
   sessions sharing that canonical state.
9. Add deterministic automated concurrency regression and a bounded owner-UAT concurrency
   scenario before R5 is resumed.

## Explicit non-solutions
- Do not weaken the active-socket collision protection.
- Do not unlink or steal a live administrator socket.
- Do not give the model administrator credentials or permission-management tools.
- Do not solve concurrency by bypassing goodLAC governance.
- Do not treat one-Pi-per-machine as an acceptable product constraint.
- Do not represent `1.0.0-rc.12` as accepted.

## Historical baseline
- accepted release: `1.0.0-rc.11`
- Phase 7 independent review: `PASS`
- R4 implementation: `6838dbf80c4d9a2572194891d3b355f39a6efbce`
- R5 source/handoff HEAD at blocker discovery: `7d4730ec430ab95ad42446af81568570e02577ea`
- target release train: `1.0.0-rc.12`
- R5 status: `BLOCKED`
