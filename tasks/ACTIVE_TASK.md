# Active Task

**Task ID:** LAC-C006

**Objective:** Implement the deterministic durable execution-lease primitive for canonical effect requests so a single-machine controller can grant at most one current short-lived executor ownership lease for a request at a time, without dispatching or executing effects.

**In scope:** versioned execution-lease domain record; durable SQLite persistence; request binding; executor identity; explicit deterministic issued/expiry times; transactional acquisition; rejection of a competing unexpired lease for the same request; deterministic expiry handling and bounded reacquisition after expiry; restart persistence; fail-closed handling of malformed/unknown request or lease state; deterministic C006 tests.

**Out of scope:** treating lease acquisition as authorization; current-policy pre-dispatch re-evaluation (`INV-006`); dispatch (`LAC-C007`); simulated or real effects; approval consumption as an execution transition; emergency pause; receipts/audit semantics beyond existing persistence; sandboxing; credentials; model/harness integration; external services; distributed consensus.

**Required inputs:** `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, controlling specification, C002 canonical effect request, C003 durable policy decision, C004 durable approval state, C005 exact approval-binding validator, and deterministic C001-C005 tests.

**Required outputs:** execution-lease domain and durable transactional lease service/repository plus deterministic C006 tests; schema migration must be migration-tested if required.

**Acceptance tests:** a durable canonical request can acquire one short-lived lease for one executor; a second competing executor cannot acquire a current unexpired lease for the same request; malformed/unknown request or lease state fails closed; lease state survives restart; explicit expiry is deterministic and permits a new bounded lease only after the prior lease is expired; lease acquisition alone cannot authorize, dispatch, or execute an effect.

**Package required?** no

**Next task on success:** `LAC-C007` dispatcher.
