from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol, runtime_checkable

from packages.core import (
    Approval,
    EffectRequest,
    EffectRequestError,
    ExecutionLease,
    ExecutionLeaseError,
    MAX_EXECUTION_LEASE_SECONDS,
    PolicyDecision,
    PolicyDecisionError,
    PolicyDecisionValue,
)
from packages.policy import PolicyDecisionProvider
from packages.state import (
    ApprovalBindingValidator,
    ApprovalRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    ExecutionLeaseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
    StateStoreError,
)


class DispatchError(RuntimeError):
    """Base fail-closed error for pre-dispatch authority failures."""


class DispatchDenied(DispatchError):
    """Current policy denies the request."""


class DispatchApprovalRequired(DispatchError):
    """Current policy requires a qualifying exact one-time approval."""


class DispatchPaused(DispatchError):
    """The durable local emergency pause blocks adapter invocation."""


class DispatchRequestExpired(DispatchError):
    """The canonical request expired before the dispatch transition."""


class DispatchAuthorityError(DispatchError):
    """Durable request/policy/approval/lease authority state did not qualify dispatch."""


class DispatchAdapterError(DispatchError):
    """The adapter contract is invalid, unsupported, or failed during invocation."""


@runtime_checkable
class EffectAdapter(Protocol):
    """C007 adapter boundary contract. Concrete effect adapters begin in C008+."""

    @property
    def adapter_id(self) -> str:
        ...

    def supports(self, request: EffectRequest) -> bool:
        ...

    def invoke(self, request: EffectRequest, *, lease: ExecutionLease) -> Any:
        ...


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DispatchError(f"{field} must be a non-empty trimmed string")
    return value


def _normalize_datetime(value: datetime, field: str) -> tuple[str, datetime]:
    if not isinstance(value, datetime):
        raise DispatchAuthorityError(f"{field} must return a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DispatchAuthorityError(f"{field} must return a timezone-aware datetime")
    normalized_dt = value.astimezone(timezone.utc)
    normalized = (
        normalized_dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    return normalized, normalized_dt


def _parse_canonical_timestamp(value: str, field: str) -> datetime:
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise DispatchAuthorityError(
            f"canonical {field} could not be interpreted"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DispatchAuthorityError(f"canonical {field} lacks timezone authority")
    return parsed.astimezone(timezone.utc)


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise DispatchAuthorityError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise DispatchAuthorityError(
            "request failed canonical integrity validation"
        ) from exc
    if canonical != request:
        raise DispatchAuthorityError("request is not canonical")
    return canonical


def _canonical_decision(decision: PolicyDecision) -> PolicyDecision:
    if not isinstance(decision, PolicyDecision):
        raise DispatchAuthorityError(
            "policy provider did not return a canonical PolicyDecision"
        )
    try:
        canonical = PolicyDecision.from_record(decision.to_record())
    except (PolicyDecisionError, TypeError, AttributeError) as exc:
        raise DispatchAuthorityError(
            "policy provider returned a malformed PolicyDecision"
        ) from exc
    if canonical != decision:
        raise DispatchAuthorityError("policy provider returned a non-canonical decision")
    return canonical


class Dispatcher:
    """Deterministic final authority gate immediately before one adapter invocation."""

    def __init__(
        self,
        *,
        store: SQLiteStateStore,
        policy_provider: PolicyDecisionProvider,
        clock: Callable[[], datetime] | None = None,
        lease_seconds: int = 30,
    ) -> None:
        if not isinstance(store, SQLiteStateStore):
            raise DispatchError("store must be a SQLiteStateStore")
        if not isinstance(policy_provider, PolicyDecisionProvider):
            raise DispatchError(
                "policy_provider must implement the PolicyDecisionProvider contract"
            )
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool):
            raise DispatchError("lease_seconds must be an integer")
        if lease_seconds <= 0 or lease_seconds > MAX_EXECUTION_LEASE_SECONDS:
            raise DispatchError(
                f"lease_seconds must be between 1 and {MAX_EXECUTION_LEASE_SECONDS}"
            )
        if clock is not None and not callable(clock):
            raise DispatchError("clock must be callable")
        self._store = store
        self._policy_provider = policy_provider
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lease_seconds = lease_seconds

    @staticmethod
    def _validate_adapter(adapter: EffectAdapter, request: EffectRequest) -> str:
        if not isinstance(adapter, EffectAdapter):
            raise DispatchAdapterError(
                "adapter does not implement the EffectAdapter contract"
            )
        try:
            adapter_id = _required_text(adapter.adapter_id, "adapter_id")
        except DispatchError as exc:
            raise DispatchAdapterError(str(exc)) from exc
        try:
            supported = adapter.supports(request)
        except Exception as exc:
            raise DispatchAdapterError("adapter support check failed closed") from exc
        if supported is not True:
            raise DispatchAdapterError(
                f"adapter {adapter_id!r} does not explicitly support this request"
            )
        return adapter_id

    def _current_revision(self) -> str:
        try:
            revision = self._policy_provider.policy_revision
        except Exception as exc:
            raise DispatchAuthorityError("current policy revision is unreadable") from exc
        try:
            return _required_text(revision, "policy_revision")
        except DispatchError as exc:
            raise DispatchAuthorityError(str(exc)) from exc

    def _now(self) -> tuple[str, datetime]:
        try:
            observed = self._clock()
        except Exception as exc:
            raise DispatchAuthorityError("trusted dispatch clock failed closed") from exc
        return _normalize_datetime(observed, "trusted dispatch clock")

    def dispatch(
        self,
        request: EffectRequest,
        *,
        adapter: EffectAdapter,
        decision_id: str,
        lease_id: str,
        executor_id: str,
        approval_id: str | None = None,
    ) -> Any:
        current_request = _canonical_request(request)
        decision_id = _required_text(decision_id, "decision_id")
        lease_id = _required_text(lease_id, "lease_id")
        executor_id = _required_text(executor_id, "executor_id")
        if approval_id is not None:
            approval_id = _required_text(approval_id, "approval_id")

        # Adapter compatibility is metadata-only. No adapter effect method is invoked here.
        self._validate_adapter(adapter, current_request)
        normalized_at, now_dt = self._now()
        request_expires_dt = _parse_canonical_timestamp(
            current_request.expires_at, "request expires_at"
        )

        failure: DispatchError | None = None
        authority_error: Exception | None = None
        acquired_lease: ExecutionLease | None = None
        revision_at_evaluation: str | None = None

        try:
            with self._store.transaction() as conn:
                durable_request = EffectRequestRepository(self._store).get(
                    current_request.request_id
                )
                if durable_request is None:
                    raise DispatchAuthorityError(
                        "current request is not durably persisted"
                    )
                if durable_request != current_request:
                    raise DispatchAuthorityError(
                        "current request differs from durable canonical state"
                    )

                revision_before = self._current_revision()
                try:
                    decision = self._policy_provider.evaluate(
                        current_request,
                        decision_id=decision_id,
                        evaluated_at=normalized_at,
                    )
                except Exception as exc:
                    raise DispatchAuthorityError(
                        "current policy evaluation failed closed"
                    ) from exc
                decision = _canonical_decision(decision)
                revision_after = self._current_revision()
                if revision_before != revision_after:
                    raise DispatchAuthorityError(
                        "policy revision changed during pre-dispatch evaluation"
                    )
                if decision.policy_revision != revision_after:
                    raise DispatchAuthorityError(
                        "policy decision does not bind the current policy revision"
                    )
                if decision.decision_id != decision_id:
                    raise DispatchAuthorityError(
                        "policy decision_id does not match the dispatch evaluation"
                    )
                if decision.request_id != current_request.request_id:
                    raise DispatchAuthorityError(
                        "policy decision binds a different request_id"
                    )
                if decision.canonical_request_hash != current_request.canonical_hash:
                    raise DispatchAuthorityError(
                        "policy decision binds a different canonical request hash"
                    )
                if decision.evaluated_at != normalized_at:
                    raise DispatchAuthorityError(
                        "policy decision timestamp does not match the trusted dispatch time"
                    )
                revision_at_evaluation = decision.policy_revision

                # The current policy decision is durable even when the gate denies or
                # otherwise refuses dispatch. This is existing policy-decision state,
                # not C010 receipt/audit expansion.
                PolicyDecisionRepository(self._store)._put_in_transaction(
                    conn, decision
                )

                if decision.decision is PolicyDecisionValue.DENY:
                    failure = DispatchDenied(
                        "current pre-dispatch policy decision is DENY"
                    )
                elif now_dt >= request_expires_dt:
                    failure = DispatchRequestExpired(
                        "canonical request expired before dispatch"
                    )
                elif (
                    decision.decision is PolicyDecisionValue.REQUIRE_APPROVAL
                    and approval_id is None
                ):
                    failure = DispatchApprovalRequired(
                        "current policy requires an exact one-time approval"
                    )
                else:
                    # Pause authority is serialized with this BEGIN IMMEDIATE transaction.
                    # A committed pause therefore blocks before approval consumption or
                    # lease acquisition; a dispatch that wins this transaction is already
                    # in-flight when a competing pause request later commits.
                    pause_state = EmergencyPauseRepository(
                        self._store
                    )._get_in_transaction(conn)
                    if pause_state.paused:
                        failure = DispatchPaused(
                            "durable local emergency pause blocks dispatch"
                        )
                    else:
                        # Approval consumption and lease acquisition are one atomic dispatch
                        # transition. If lease acquisition fails, consumption is rolled back,
                        # while the current policy decision remains durable.
                        conn.execute("SAVEPOINT lac_dispatch_authority")
                        try:
                            if decision.decision is PolicyDecisionValue.REQUIRE_APPROVAL:
                                assert approval_id is not None
                                approval: Approval = ApprovalBindingValidator(
                                    self._store
                                ).validate(
                                    approval_id=approval_id,
                                    current_request=current_request,
                                    at=normalized_at,
                                )
                                ApprovalRepository(
                                    self._store
                                )._consume_once_in_transaction(
                                    conn,
                                    approval,
                                    consumed_at=normalized_at,
                                )
                            elif decision.decision is not PolicyDecisionValue.ALLOW:
                                raise DispatchAuthorityError(
                                    "unknown policy decision state fails closed"
                                )

                            lease_expires_dt = min(
                                now_dt + timedelta(seconds=self._lease_seconds),
                                request_expires_dt,
                            )
                            lease_expires_at = (
                                lease_expires_dt.isoformat(timespec="microseconds")
                                .replace("+00:00", "Z")
                            )
                            try:
                                lease = ExecutionLease.create(
                                    lease_id=lease_id,
                                    request_id=current_request.request_id,
                                    executor_id=executor_id,
                                    issued_at=normalized_at,
                                    expires_at=lease_expires_at,
                                )
                            except ExecutionLeaseError as exc:
                                raise DispatchAuthorityError(
                                    "execution lease could not be formed from current authority state"
                                ) from exc
                            acquired_lease = ExecutionLeaseRepository(
                                self._store
                            )._acquire_in_transaction(conn, lease)
                        except Exception as exc:
                            conn.execute("ROLLBACK TO SAVEPOINT lac_dispatch_authority")
                            conn.execute("RELEASE SAVEPOINT lac_dispatch_authority")
                            authority_error = exc
                            acquired_lease = None
                        else:
                            conn.execute("RELEASE SAVEPOINT lac_dispatch_authority")
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError(
                "durable dispatcher state failed closed"
            ) from exc

        if failure is not None:
            raise failure
        if authority_error is not None:
            if isinstance(authority_error, DispatchError):
                raise authority_error
            raise DispatchAuthorityError(
                "approval or execution-lease transition failed closed"
            ) from authority_error
        if acquired_lease is None or revision_at_evaluation is None:
            raise DispatchAuthorityError(
                "dispatch transition completed without durable authority state"
            )

        # The invocation gate is a second short BEGIN IMMEDIATE transaction. The lease
        # is already durable before the effect call, while pause/resume writers are
        # serialized until invoke returns. If pause committed in the handoff gap, the
        # adapter is conservatively not invoked; resume never auto-runs that request.
        adapter_result: Any = None
        adapter_error: Exception | None = None
        try:
            with self._store.transaction() as conn:
                if self._current_revision() != revision_at_evaluation:
                    raise DispatchAuthorityError(
                        "policy revision changed before adapter invocation"
                    )
                pause_state = EmergencyPauseRepository(
                    self._store
                )._get_in_transaction(conn)
                if pause_state.paused:
                    raise DispatchPaused(
                        "durable local emergency pause blocks adapter invocation"
                    )
                try:
                    adapter_result = adapter.invoke(
                        current_request, lease=acquired_lease
                    )
                except Exception as exc:
                    adapter_error = exc
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError(
                "durable emergency-pause invocation gate failed closed"
            ) from exc
        except Exception as exc:
            raise DispatchAuthorityError(
                "emergency-pause invocation gate failed closed"
            ) from exc

        if adapter_error is not None:
            raise DispatchAdapterError(
                "adapter invocation failed after the durable dispatch transition"
            ) from adapter_error
        return adapter_result
