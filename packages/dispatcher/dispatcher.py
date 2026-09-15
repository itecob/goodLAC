from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol, runtime_checkable

from packages.capabilities import (
    CapabilityRequestContext,
    CapabilityRequestDenied,
    CapabilityRequestError,
    CapabilityRequestValidator,
    PendingPermissionRepository,
)
from packages.core import (
    Approval,
    EffectExecution,
    EffectExecutionState,
    EffectOutcome,
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
    AgentIdentityRepository,
    AgentStatus,
    ApprovalBindingValidator,
    ApprovalRepository,
    AuditRepository,
    EffectExecutionTransitionError,
    EffectIdempotencyConflict,
    EffectReceiptRepository,
    EffectReceiptStateError,
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


class DispatchCapabilityDenied(DispatchDenied):
    # P002 capability validation terminally closed this effect request.
    pass


class DispatchAgentRevoked(DispatchDenied):
    """The durable controller-owned agent identity is revoked."""


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


class DispatchDuplicateEffect(DispatchAuthorityError):
    """The governed effect is already terminal or its idempotency key is already bound."""


class DispatchReconciliationRequired(DispatchAuthorityError):
    """Durable state is non-terminal and cannot be safely advanced by this adapter."""


@runtime_checkable
class EffectAdapter(Protocol):
    """Bounded adapter boundary. Invocation is permitted only by Dispatcher."""

    @property
    def adapter_id(self) -> str:
        ...

    def supports(self, request: EffectRequest) -> bool:
        ...

    def invoke(self, request: EffectRequest, *, lease: ExecutionLease) -> Any:
        ...


@runtime_checkable
class ReconciliationEffectAdapter(Protocol):
    """Optional read-only/safe reconciliation surface for ambiguous PREPARED state."""

    def reconcile(self, request: EffectRequest, *, lease: ExecutionLease) -> Any | None:
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
    normalized = normalized_dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return normalized, normalized_dt


def _parse_canonical_timestamp(value: str, field: str) -> datetime:
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise DispatchAuthorityError(f"canonical {field} could not be interpreted") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DispatchAuthorityError(f"canonical {field} lacks timezone authority")
    return parsed.astimezone(timezone.utc)


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise DispatchAuthorityError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise DispatchAuthorityError("request failed canonical integrity validation") from exc
    if canonical != request:
        raise DispatchAuthorityError("request is not canonical")
    return canonical


def _canonical_decision(decision: PolicyDecision) -> PolicyDecision:
    if not isinstance(decision, PolicyDecision):
        raise DispatchAuthorityError("policy provider did not return a canonical PolicyDecision")
    try:
        canonical = PolicyDecision.from_record(decision.to_record())
    except (PolicyDecisionError, TypeError, AttributeError) as exc:
        raise DispatchAuthorityError("policy provider returned a malformed PolicyDecision") from exc
    if canonical != decision:
        raise DispatchAuthorityError("policy provider returned a non-canonical decision")
    return canonical


def _upstream_reference(result: Any) -> str | None:
    value = None
    if isinstance(result, dict):
        value = result.get("upstream_reference")
    elif hasattr(result, "upstream_reference"):
        value = getattr(result, "upstream_reference")
    if value is None:
        return None
    try:
        return _required_text(value, "upstream_reference")
    except DispatchError as exc:
        raise DispatchAdapterError("adapter returned an invalid upstream_reference") from exc


class Dispatcher:
    """Deterministic final authority gate with durable exactly-once/reconciliation state."""

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
            raise DispatchError("policy_provider must implement the PolicyDecisionProvider contract")
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
            raise DispatchAdapterError("adapter does not implement the EffectAdapter contract")
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

    def _require_active_agent(self, request: EffectRequest) -> None:
        try:
            identity = AgentIdentityRepository(self._store).get(request.agent_id)
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable agent identity failed closed") from exc
        if identity is None:
            raise DispatchAuthorityError(
                "policy-authorized agent has no durable controller identity"
            )
        if identity.principal_id != request.principal_id:
            raise DispatchAuthorityError(
                "durable agent identity binds a different principal"
            )
        if identity.status is AgentStatus.REVOKED:
            raise DispatchAgentRevoked("durable agent identity is revoked")
        if identity.status is not AgentStatus.ACTIVE:
            raise DispatchAuthorityError("unknown durable agent status fails closed")

    def _evaluate_current_policy(
        self,
        request: EffectRequest,
        *,
        decision_id: str,
        evaluated_at: str,
    ) -> tuple[PolicyDecision, str]:
        revision_before = self._current_revision()
        try:
            decision = self._policy_provider.evaluate(
                request, decision_id=decision_id, evaluated_at=evaluated_at
            )
        except Exception as exc:
            raise DispatchAuthorityError("current policy evaluation failed closed") from exc
        decision = _canonical_decision(decision)
        revision_after = self._current_revision()
        if revision_before != revision_after:
            raise DispatchAuthorityError("policy revision changed during pre-dispatch evaluation")
        if decision.policy_revision != revision_after:
            raise DispatchAuthorityError("policy decision does not bind the current policy revision")
        if decision.decision_id != decision_id:
            raise DispatchAuthorityError("policy decision_id does not match the dispatch evaluation")
        if decision.request_id != request.request_id:
            raise DispatchAuthorityError("policy decision binds a different request_id")
        if decision.canonical_request_hash != request.canonical_hash:
            raise DispatchAuthorityError("policy decision binds a different canonical request hash")
        if decision.evaluated_at != evaluated_at:
            raise DispatchAuthorityError(
                "policy decision timestamp does not match the trusted dispatch time"
            )
        return decision, revision_after

    def _validate_consumed_reserved_approval(
        self, execution: EffectExecution, *, approval_id: str | None
    ) -> None:
        if execution.approval_id is None:
            raise DispatchApprovalRequired(
                "recovery under REQUIRE_APPROVAL has no reserved exact approval"
            )
        if approval_id is not None and approval_id != execution.approval_id:
            raise DispatchAuthorityError("recovery approval_id differs from reserved approval")
        approval = ApprovalRepository(self._store).get(execution.approval_id)
        if approval is None:
            raise DispatchAuthorityError("reserved approval disappeared from durable state")
        if (
            approval.request_id != execution.request_id
            or approval.canonical_request_hash != execution.canonical_request_hash
            or approval.consumed_at is None
            or approval.consumed_at != execution.leased_at
        ):
            raise DispatchAuthorityError("reserved approval no longer binds leased execution")

    def _reconcile_prepared(
        self,
        request: EffectRequest,
        *,
        adapter: EffectAdapter,
        execution: EffectExecution,
    ) -> Any:
        if not isinstance(adapter, ReconciliationEffectAdapter):
            raise DispatchReconciliationRequired(
                "PREPARED execution is ambiguous and adapter exposes no safe reconciliation"
            )
        lease = ExecutionLeaseRepository(self._store).get(execution.lease_id)
        if lease is None:
            raise DispatchAuthorityError("PREPARED execution lost its durable lease")
        try:
            reconciled = adapter.reconcile(request, lease=lease)
        except Exception as exc:
            try:
                failed_at, _ = self._now()
                with self._store.transaction() as conn:
                    AuditRepository(self._store)._append_in_transaction(
                        conn,
                        request_id=request.request_id,
                        event_type="EFFECT_RECONCILIATION_FAILED",
                        occurred_at=failed_at,
                        details={"adapter_id": execution.adapter_id, "state": execution.state.value},
                    )
            except Exception:
                pass
            raise DispatchReconciliationRequired("safe adapter reconciliation failed closed") from exc
        if reconciled is None:
            raise DispatchReconciliationRequired("adapter could not determine PREPARED effect outcome")
        upstream_reference = _upstream_reference(reconciled)
        completed_at, _ = self._now()
        try:
            with self._store.transaction() as conn:
                current = EffectReceiptRepository(self._store).get_execution(request.request_id)
                if current is None:
                    raise DispatchAuthorityError("PREPARED execution disappeared during reconciliation")
                terminal, _receipt = EffectReceiptRepository(self._store)._complete_in_transaction(
                    conn,
                    current,
                    outcome=EffectOutcome.SUCCEEDED,
                    result=reconciled,
                    completed_at=completed_at,
                    upstream_reference=upstream_reference,
                )
                AuditRepository(self._store)._append_in_transaction(
                    conn,
                    request_id=request.request_id,
                    event_type="EFFECT_RECONCILED_SUCCEEDED",
                    occurred_at=completed_at,
                    details={
                        "adapter_id": terminal.adapter_id,
                        "receipt_id": terminal.receipt_id,
                        "input_hash": terminal.input_hash,
                    },
                )
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable reconciliation state failed closed") from exc
        return reconciled

    def _prepare_recovery_from_leased(
        self,
        request: EffectRequest,
        *,
        execution: EffectExecution,
        decision_id: str,
        approval_id: str | None,
        normalized_at: str,
        now_dt: datetime,
        request_expires_dt: datetime,
    ) -> tuple[EffectExecution, str]:
        failure: DispatchError | None = None
        prepared: EffectExecution | None = None
        revision: str | None = None
        try:
            with self._store.transaction() as conn:
                current = EffectReceiptRepository(self._store).get_execution(request.request_id)
                if current != execution or current.state is not EffectExecutionState.LEASED:
                    raise DispatchAuthorityError("LEASED recovery state changed before re-evaluation")
                decision, revision = self._evaluate_current_policy(
                    request, decision_id=decision_id, evaluated_at=normalized_at
                )
                PolicyDecisionRepository(self._store)._put_in_transaction(conn, decision)
                if decision.decision is not PolicyDecisionValue.DENY:
                    self._require_active_agent(request)
                if decision.decision is PolicyDecisionValue.DENY:
                    failure = DispatchDenied("current pre-dispatch policy decision is DENY")
                elif now_dt >= request_expires_dt:
                    failure = DispatchRequestExpired("canonical request expired before recovery")
                else:
                    pause_state = EmergencyPauseRepository(self._store)._get_in_transaction(conn)
                    if pause_state.paused:
                        failure = DispatchPaused("durable local emergency pause blocks recovery")
                    else:
                        lease = ExecutionLeaseRepository(self._store).get(current.lease_id)
                        if lease is None or lease.is_expired(normalized_at):
                            failure = DispatchReconciliationRequired(
                                "LEASED execution expired before invocation; new authority is required"
                            )
                        elif decision.decision is PolicyDecisionValue.REQUIRE_APPROVAL:
                            self._validate_consumed_reserved_approval(
                                current, approval_id=approval_id
                            )
                        elif decision.decision is not PolicyDecisionValue.ALLOW:
                            raise DispatchAuthorityError("unknown policy decision state fails closed")
                        if failure is None:
                            prepared = EffectReceiptRepository(self._store)._mark_prepared_in_transaction(
                                conn, current, prepared_at=normalized_at
                            )
                            AuditRepository(self._store)._append_in_transaction(
                                conn,
                                request_id=request.request_id,
                                event_type="EFFECT_PREPARED",
                                occurred_at=normalized_at,
                                details={
                                    "adapter_id": prepared.adapter_id,
                                    "lease_id": prepared.lease_id,
                                    "recovery": True,
                                },
                            )
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable LEASED recovery failed closed") from exc
        if failure is not None:
            raise failure
        if prepared is None or revision is None:
            raise DispatchAuthorityError("LEASED recovery completed without prepared execution")
        return prepared, revision

    def _invoke_prepared(
        self,
        request: EffectRequest,
        *,
        adapter: EffectAdapter,
        execution: EffectExecution,
        revision_at_evaluation: str,
    ) -> Any:
        adapter_result: Any = None
        adapter_error: Exception | None = None
        preinvoke_failure: DispatchError | None = None
        request_expires_dt = _parse_canonical_timestamp(request.expires_at, "request expires_at")
        try:
            with self._store.transaction() as conn:
                if self._current_revision() != revision_at_evaluation:
                    raise DispatchAuthorityError("policy revision changed before adapter invocation")
                pause_state = EmergencyPauseRepository(self._store)._get_in_transaction(conn)
                if pause_state.paused:
                    raise DispatchPaused("durable local emergency pause blocks adapter invocation")
                current = EffectReceiptRepository(self._store).get_execution(request.request_id)
                if current != execution or current.state is not EffectExecutionState.PREPARED:
                    raise DispatchAuthorityError("prepared execution changed before adapter invocation")
                lease = ExecutionLeaseRepository(self._store).get(current.lease_id)
                if lease is None:
                    raise DispatchAuthorityError("prepared execution lost durable lease")

                try:
                    self._require_active_agent(request)
                except DispatchError as exc:
                    preinvoke_failure = exc

                # Fresh trusted time at the last deterministic controller gate before
                # a new adapter invocation begins closes the suspension/scheduling gap.
                invocation_at, invocation_dt = self._now()
                if preinvoke_failure is None and invocation_dt >= request_expires_dt:
                    preinvoke_failure = DispatchRequestExpired(
                        "canonical request expired before adapter invocation"
                    )
                if preinvoke_failure is None and lease.is_expired(invocation_at):
                    preinvoke_failure = DispatchReconciliationRequired(
                        "execution lease expired before adapter invocation; new invocation is forbidden"
                    )

                if preinvoke_failure is not None:
                    # PREPARED is generally ambiguous. Here invoke() provably has not
                    # begun, so restoring LEASED prevents a retry from reconciling a
                    # false simulated success while keeping the state recoverable.
                    restored = EffectReceiptRepository(
                        self._store
                    )._restore_leased_before_invocation_in_transaction(conn, current)
                    AuditRepository(self._store)._append_in_transaction(
                        conn,
                        request_id=request.request_id,
                        event_type="EFFECT_PREINVOCATION_BLOCKED",
                        occurred_at=invocation_at,
                        details={
                            "adapter_id": restored.adapter_id,
                            "lease_id": restored.lease_id,
                            "restored_state": restored.state.value,
                            "reason": type(preinvoke_failure).__name__,
                        },
                    )
                else:
                    try:
                        adapter_result = adapter.invoke(request, lease=lease)
                    except Exception as exc:
                        adapter_error = exc
                        failure_result = {"error_code": "ADAPTER_INVOCATION_FAILED"}
                        completed_at, _ = self._now()
                        terminal, _receipt = EffectReceiptRepository(
                            self._store
                        )._complete_in_transaction(
                            conn,
                            current,
                            outcome=EffectOutcome.FAILED,
                            result=failure_result,
                            completed_at=completed_at,
                        )
                        AuditRepository(self._store)._append_in_transaction(
                            conn,
                            request_id=request.request_id,
                            event_type="EFFECT_FAILED",
                            occurred_at=completed_at,
                            details={
                                "adapter_id": terminal.adapter_id,
                                "receipt_id": terminal.receipt_id,
                                "error_code": "ADAPTER_INVOCATION_FAILED",
                            },
                        )
                    else:
                        completed_at, _ = self._now()
                        upstream_reference = _upstream_reference(adapter_result)
                        terminal, _receipt = EffectReceiptRepository(
                            self._store
                        )._complete_in_transaction(
                            conn,
                            current,
                            outcome=EffectOutcome.SUCCEEDED,
                            result=adapter_result,
                            completed_at=completed_at,
                            upstream_reference=upstream_reference,
                        )
                        AuditRepository(self._store)._append_in_transaction(
                            conn,
                            request_id=request.request_id,
                            event_type="EFFECT_SUCCEEDED",
                            occurred_at=completed_at,
                            details={
                                "adapter_id": terminal.adapter_id,
                                "receipt_id": terminal.receipt_id,
                                "result_hash": EffectReceiptRepository(self._store)
                                .get_receipt(terminal.receipt_id)
                                .result_hash,
                            },
                        )
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable effect receipt/audit transition failed closed") from exc
        except Exception as exc:
            raise DispatchAuthorityError("effect invocation gate failed closed") from exc

        if preinvoke_failure is not None:
            raise preinvoke_failure
        if adapter_error is not None:
            raise DispatchAdapterError(
                "adapter invocation failed after the durable dispatch transition"
            ) from adapter_error
        return adapter_result

    def dispatch_capability(
        self,
        request: EffectRequest,
        *,
        capability_context: CapabilityRequestContext,
        adapter: EffectAdapter,
        decision_id: str,
        lease_id: str,
        executor_id: str,
        approval_id: str | None = None,
    ) -> Any:
        current_request = _canonical_request(request)
        normalized_at, _ = self._now()
        try:
            CapabilityRequestValidator(self._store).validate_or_quarantine(
                current_request,
                context=capability_context,
                observed_at_utc=normalized_at,
            )
        except CapabilityRequestDenied as exc:
            raise DispatchCapabilityDenied(str(exc)) from exc
        except CapabilityRequestError as exc:
            raise DispatchAuthorityError(
                "capability validation durable state failed closed"
            ) from exc
        return self.dispatch(
            current_request,
            adapter=adapter,
            decision_id=decision_id,
            lease_id=lease_id,
            executor_id=executor_id,
            approval_id=approval_id,
        )

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
        # A terminal P002 capability denial is immutable authority state.
        try:
            closure = PendingPermissionRepository(self._store).get_closure(
                current_request.request_id
            )
        except CapabilityRequestError as exc:
            raise DispatchAuthorityError(
                "capability-denial closure state failed closed"
            ) from exc
        if closure is not None:
            if closure["canonical_request_hash"] != current_request.canonical_hash:
                raise DispatchAuthorityError(
                    "closed request_id is bound to a different canonical request"
                )
            raise DispatchCapabilityDenied(
                "terminal P002 capability denial: "
                + str(closure["reason"])
                + " pending_id="
                + str(closure["pending_id"])
            )
        decision_id = _required_text(decision_id, "decision_id")
        lease_id = _required_text(lease_id, "lease_id")
        executor_id = _required_text(executor_id, "executor_id")
        if approval_id is not None:
            approval_id = _required_text(approval_id, "approval_id")

        adapter_id = self._validate_adapter(adapter, current_request)
        normalized_at, now_dt = self._now()
        request_expires_dt = _parse_canonical_timestamp(
            current_request.expires_at, "request expires_at"
        )

        # Canonical execution state, not audit, drives duplicate/restart behavior.
        try:
            receipts = EffectReceiptRepository(self._store)
            existing = receipts.get_execution(current_request.request_id)
            by_key = receipts.get_by_idempotency(adapter_id, current_request.idempotency_key)
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable effect execution state failed closed") from exc
        if by_key is not None and by_key.request_id != current_request.request_id:
            raise DispatchDuplicateEffect(
                "adapter/idempotency key already belongs to a different governed request"
            )
        if existing is not None:
            if (
                existing.adapter_id != adapter_id
                or existing.canonical_request_hash != current_request.canonical_hash
                or existing.idempotency_key != current_request.idempotency_key
            ):
                raise DispatchAuthorityError("existing effect execution does not bind current request")
            if existing.state in (EffectExecutionState.SUCCEEDED, EffectExecutionState.FAILED):
                raise DispatchDuplicateEffect(
                    f"governed effect is already terminal: {existing.state.value}"
                )
            if existing.state is EffectExecutionState.PREPARED:
                return self._reconcile_prepared(
                    current_request,
                    adapter=adapter,
                    execution=existing,
                )
            if existing.state is EffectExecutionState.LEASED:
                prepared, revision = self._prepare_recovery_from_leased(
                    current_request,
                    execution=existing,
                    decision_id=decision_id,
                    approval_id=approval_id,
                    normalized_at=normalized_at,
                    now_dt=now_dt,
                    request_expires_dt=request_expires_dt,
                )
                return self._invoke_prepared(
                    current_request,
                    adapter=adapter,
                    execution=prepared,
                    revision_at_evaluation=revision,
                )
            raise DispatchAuthorityError("unknown durable effect execution state fails closed")

        failure: DispatchError | None = None
        authority_error: Exception | None = None
        acquired_lease: ExecutionLease | None = None
        execution: EffectExecution | None = None
        revision_at_evaluation: str | None = None

        try:
            with self._store.transaction() as conn:
                durable_request = EffectRequestRepository(self._store).get(
                    current_request.request_id
                )
                if durable_request is None:
                    raise DispatchAuthorityError("current request is not durably persisted")
                if durable_request != current_request:
                    raise DispatchAuthorityError(
                        "current request differs from durable canonical state"
                    )

                decision, revision_at_evaluation = self._evaluate_current_policy(
                    current_request,
                    decision_id=decision_id,
                    evaluated_at=normalized_at,
                )
                PolicyDecisionRepository(self._store)._put_in_transaction(conn, decision)
                if decision.decision is not PolicyDecisionValue.DENY:
                    self._require_active_agent(current_request)

                if decision.decision is PolicyDecisionValue.DENY:
                    failure = DispatchDenied("current pre-dispatch policy decision is DENY")
                elif now_dt >= request_expires_dt:
                    failure = DispatchRequestExpired("canonical request expired before dispatch")
                elif (
                    decision.decision is PolicyDecisionValue.REQUIRE_APPROVAL
                    and approval_id is None
                ):
                    failure = DispatchApprovalRequired(
                        "current policy requires an exact one-time approval"
                    )
                else:
                    pause_state = EmergencyPauseRepository(self._store)._get_in_transaction(conn)
                    if pause_state.paused:
                        failure = DispatchPaused("durable local emergency pause blocks dispatch")
                    else:
                        conn.execute("SAVEPOINT lac_dispatch_authority")
                        try:
                            reserved_approval_id: str | None = None
                            if decision.decision is PolicyDecisionValue.REQUIRE_APPROVAL:
                                assert approval_id is not None
                                approval: Approval = ApprovalBindingValidator(self._store).validate(
                                    approval_id=approval_id,
                                    current_request=current_request,
                                    at=normalized_at,
                                )
                                ApprovalRepository(self._store)._consume_once_in_transaction(
                                    conn, approval, consumed_at=normalized_at
                                )
                                reserved_approval_id = approval.approval_id
                            elif decision.decision is not PolicyDecisionValue.ALLOW:
                                raise DispatchAuthorityError(
                                    "unknown policy decision state fails closed"
                                )

                            lease_expires_dt = min(
                                now_dt + timedelta(seconds=self._lease_seconds),
                                request_expires_dt,
                            )
                            lease_expires_at = lease_expires_dt.isoformat(
                                timespec="microseconds"
                            ).replace("+00:00", "Z")
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
                            execution = EffectReceiptRepository(
                                self._store
                            )._record_leased_in_transaction(
                                conn,
                                request=current_request,
                                adapter_id=adapter_id,
                                lease=acquired_lease,
                                approval_id=reserved_approval_id,
                                leased_at=normalized_at,
                            )
                            AuditRepository(self._store)._append_in_transaction(
                                conn,
                                request_id=current_request.request_id,
                                event_type="EFFECT_LEASED",
                                occurred_at=normalized_at,
                                details={
                                    "adapter_id": adapter_id,
                                    "lease_id": acquired_lease.lease_id,
                                    "input_hash": execution.input_hash,
                                },
                            )
                        except Exception as exc:
                            conn.execute("ROLLBACK TO SAVEPOINT lac_dispatch_authority")
                            conn.execute("RELEASE SAVEPOINT lac_dispatch_authority")
                            authority_error = exc
                            acquired_lease = None
                            execution = None
                        else:
                            conn.execute("RELEASE SAVEPOINT lac_dispatch_authority")
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable dispatcher state failed closed") from exc

        if failure is not None:
            raise failure
        if authority_error is not None:
            if isinstance(authority_error, DispatchError):
                raise authority_error
            if isinstance(authority_error, EffectIdempotencyConflict):
                raise DispatchDuplicateEffect(str(authority_error)) from authority_error
            raise DispatchAuthorityError(
                "approval, execution-lease, or effect-state transition failed closed"
            ) from authority_error
        if (
            acquired_lease is None
            or execution is None
            or revision_at_evaluation is None
        ):
            raise DispatchAuthorityError(
                "dispatch transition completed without durable authority/effect state"
            )

        # Persist PREPARED before any adapter call. A crash from this point onward is
        # ambiguous by design and must reconcile; it is never interpreted as success.
        try:
            with self._store.transaction() as conn:
                if self._current_revision() != revision_at_evaluation:
                    raise DispatchAuthorityError("policy revision changed before effect prepare")
                pause_state = EmergencyPauseRepository(self._store)._get_in_transaction(conn)
                if pause_state.paused:
                    raise DispatchPaused("durable local emergency pause blocks adapter invocation")
                current = EffectReceiptRepository(self._store).get_execution(
                    current_request.request_id
                )
                if current != execution:
                    raise DispatchAuthorityError("effect execution changed before prepare")
                prepared = EffectReceiptRepository(self._store)._mark_prepared_in_transaction(
                    conn, current, prepared_at=normalized_at
                )
                AuditRepository(self._store)._append_in_transaction(
                    conn,
                    request_id=current_request.request_id,
                    event_type="EFFECT_PREPARED",
                    occurred_at=normalized_at,
                    details={
                        "adapter_id": adapter_id,
                        "lease_id": prepared.lease_id,
                        "recovery": False,
                    },
                )
        except DispatchError:
            raise
        except StateStoreError as exc:
            raise DispatchAuthorityError("durable effect prepare failed closed") from exc

        return self._invoke_prepared(
            current_request,
            adapter=adapter,
            execution=prepared,
            revision_at_evaluation=revision_at_evaluation,
        )
