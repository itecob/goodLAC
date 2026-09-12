from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from packages.core import (
    EffectExecution,
    EffectExecutionState,
    EffectOutcome,
    EffectReceipt,
    EffectReceiptError,
    EffectRequest,
    ExecutionLease,
    canonical_json,
    canonical_result_json,
    deterministic_receipt_id,
    result_hash_for_json,
)
from .approvals import ApprovalRepository
from .effect_requests import EffectRequestRepository
from .execution_leases import ExecutionLeaseRepository
from .store import SQLiteStateStore, StateStoreError


class EffectReceiptStateError(StateStoreError):
    """Persisted execution/receipt state is malformed or internally inconsistent."""


class EffectIdempotencyConflict(StateStoreError):
    """An adapter/idempotency key is already bound to different canonical request material."""


class EffectExecutionTransitionError(StateStoreError):
    """A requested canonical execution transition is invalid or unsafe."""


def _hash_record(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def lease_hash(lease: ExecutionLease) -> str:
    return _hash_record(lease.to_record())


def effect_input_hash(request: EffectRequest, adapter_id: str, lease: ExecutionLease) -> str:
    return _hash_record(
        {
            "canonical_request_hash": request.canonical_hash,
            "adapter_id": adapter_id,
            "lease": lease.to_record(),
        }
    )


class EffectReceiptRepository:
    """Canonical execution and terminal receipt state. Audit never participates in authority."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    @staticmethod
    def _decode_execution(row: sqlite3.Row) -> EffectExecution:
        try:
            return EffectExecution.from_record(dict(row))
        except EffectReceiptError as exc:
            raise EffectReceiptStateError(
                "persisted effect execution failed integrity validation"
            ) from exc

    @staticmethod
    def _decode_receipt(row: sqlite3.Row) -> EffectReceipt:
        try:
            return EffectReceipt.from_record(dict(row))
        except EffectReceiptError as exc:
            raise EffectReceiptStateError(
                "persisted effect receipt failed integrity validation"
            ) from exc

    def _validate_execution_bindings(
        self, execution: EffectExecution
    ) -> tuple[EffectRequest, ExecutionLease]:
        request = EffectRequestRepository(self._store).get(execution.request_id)
        if request is None or request.canonical_hash != execution.canonical_request_hash:
            raise EffectReceiptStateError("effect execution lost canonical request binding")
        if request.idempotency_key != execution.idempotency_key:
            raise EffectReceiptStateError("effect execution idempotency binding changed")
        lease = ExecutionLeaseRepository(self._store).get(execution.lease_id)
        if lease is None or lease.request_id != request.request_id:
            raise EffectReceiptStateError("effect execution lost execution-lease binding")
        if lease.issued_at != execution.leased_at:
            raise EffectReceiptStateError("effect execution leased_at does not match durable lease")
        observed_lease_hash = lease_hash(lease)
        if observed_lease_hash != execution.lease_hash:
            raise EffectReceiptStateError("effect execution lease hash does not match durable lease")
        if execution.approval_id is not None:
            approval = ApprovalRepository(self._store).get(execution.approval_id)
            if approval is None:
                raise EffectReceiptStateError("effect execution lost approval binding")
            if (
                approval.request_id != execution.request_id
                or approval.canonical_request_hash != execution.canonical_request_hash
                or approval.consumed_at != execution.leased_at
            ):
                raise EffectReceiptStateError("effect execution approval binding is inconsistent")
        expected_input_hash = effect_input_hash(request, execution.adapter_id, lease)
        if expected_input_hash != execution.input_hash:
            raise EffectReceiptStateError("effect execution input hash is inconsistent")
        return request, lease

    def _validate_terminal_receipt(self, execution: EffectExecution) -> EffectReceipt:
        if execution.state not in (EffectExecutionState.SUCCEEDED, EffectExecutionState.FAILED):
            raise EffectReceiptStateError("non-terminal execution cannot bind a terminal receipt")
        if execution.receipt_id is None:
            raise EffectReceiptStateError("terminal execution is missing receipt identity")
        receipt = self.get_receipt(execution.receipt_id)
        if receipt is None:
            raise EffectReceiptStateError("terminal execution receipt row is missing")
        expected_outcome = (
            EffectOutcome.SUCCEEDED
            if execution.state is EffectExecutionState.SUCCEEDED
            else EffectOutcome.FAILED
        )
        if (
            receipt.request_id != execution.request_id
            or receipt.canonical_request_hash != execution.canonical_request_hash
            or receipt.idempotency_key != execution.idempotency_key
            or receipt.approval_id != execution.approval_id
            or receipt.adapter_id != execution.adapter_id
            or receipt.lease_id != execution.lease_id
            or receipt.input_hash != execution.input_hash
            or receipt.started_at != execution.prepared_at
            or receipt.completed_at != execution.completed_at
            or receipt.outcome is not expected_outcome
        ):
            raise EffectReceiptStateError("terminal receipt does not bind canonical execution state")
        return receipt

    def get_execution(self, request_id: str) -> EffectExecution | None:
        if not isinstance(request_id, str) or not request_id:
            raise StateStoreError("request_id must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, request_id, canonical_request_hash, idempotency_key,
                   adapter_id, lease_id, lease_hash, input_hash, approval_id,
                   state, leased_at, prepared_at, completed_at, receipt_id
            FROM effect_executions WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            return None
        execution = self._decode_execution(row)
        self._validate_execution_bindings(execution)
        if execution.state in (EffectExecutionState.SUCCEEDED, EffectExecutionState.FAILED):
            self._validate_terminal_receipt(execution)
        return execution

    def get_by_idempotency(self, adapter_id: str, idempotency_key: str) -> EffectExecution | None:
        if not isinstance(adapter_id, str) or not adapter_id:
            raise StateStoreError("adapter_id must be a non-empty string")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise StateStoreError("idempotency_key must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, request_id, canonical_request_hash, idempotency_key,
                   adapter_id, lease_id, lease_hash, input_hash, approval_id,
                   state, leased_at, prepared_at, completed_at, receipt_id
            FROM effect_executions
            WHERE adapter_id = ? AND idempotency_key = ?
            """,
            (adapter_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        execution = self._decode_execution(row)
        self._validate_execution_bindings(execution)
        if execution.state in (EffectExecutionState.SUCCEEDED, EffectExecutionState.FAILED):
            self._validate_terminal_receipt(execution)
        return execution

    def get_receipt(self, receipt_id: str) -> EffectReceipt | None:
        if not isinstance(receipt_id, str) or not receipt_id:
            raise StateStoreError("receipt_id must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, receipt_id, request_id, canonical_request_hash,
                   idempotency_key, approval_id, adapter_id, lease_id, input_hash,
                   started_at, completed_at, outcome, result_json, result_hash,
                   upstream_reference
            FROM effect_receipts WHERE receipt_id = ?
            """,
            (receipt_id,),
        ).fetchone()
        if row is None:
            return None
        receipt = self._decode_receipt(row)
        request = EffectRequestRepository(self._store).get(receipt.request_id)
        if request is None or request.canonical_hash != receipt.canonical_request_hash:
            raise EffectReceiptStateError("effect receipt lost canonical request binding")
        if request.idempotency_key != receipt.idempotency_key:
            raise EffectReceiptStateError("effect receipt idempotency binding changed")
        lease = ExecutionLeaseRepository(self._store).get(receipt.lease_id)
        if lease is None or lease.request_id != receipt.request_id:
            raise EffectReceiptStateError("effect receipt lost execution-lease binding")
        if effect_input_hash(request, receipt.adapter_id, lease) != receipt.input_hash:
            raise EffectReceiptStateError("effect receipt canonical input binding changed")
        return receipt

    def get_receipt_for_request(self, request_id: str) -> EffectReceipt | None:
        execution = self.get_execution(request_id)
        if execution is None or execution.receipt_id is None:
            return None
        return self._validate_terminal_receipt(execution)

    def _record_leased_in_transaction(
        self,
        conn: sqlite3.Connection,
        *,
        request: EffectRequest,
        adapter_id: str,
        lease: ExecutionLease,
        approval_id: str | None,
        leased_at: str,
    ) -> EffectExecution:
        if conn is not self._store._conn or not conn.in_transaction:
            raise EffectExecutionTransitionError(
                "execution transition requires the active StateStore transaction"
            )
        durable_request = EffectRequestRepository(self._store).get(request.request_id)
        if durable_request != request:
            raise EffectExecutionTransitionError("execution request is not current durable canonical state")
        durable_lease = ExecutionLeaseRepository(self._store).get(lease.lease_id)
        if durable_lease != lease or lease.request_id != request.request_id:
            raise EffectExecutionTransitionError("execution lease is not current durable canonical state")
        candidate = EffectExecution.create(
            request_id=request.request_id,
            canonical_request_hash=request.canonical_hash,
            idempotency_key=request.idempotency_key,
            adapter_id=adapter_id,
            lease_id=lease.lease_id,
            lease_hash=lease_hash(lease),
            input_hash=effect_input_hash(request, adapter_id, lease),
            approval_id=approval_id,
            state=EffectExecutionState.LEASED,
            leased_at=leased_at,
        )
        existing = self.get_execution(request.request_id)
        if existing is not None:
            if existing != candidate:
                raise EffectExecutionTransitionError(
                    "request already has different canonical effect execution state"
                )
            return existing
        other = self.get_by_idempotency(adapter_id, request.idempotency_key)
        if other is not None and other.request_id != request.request_id:
            raise EffectIdempotencyConflict(
                "adapter/idempotency key already binds a different request"
            )
        try:
            conn.execute(
                """
                INSERT INTO effect_executions(
                    schema, request_id, canonical_request_hash, idempotency_key,
                    adapter_id, lease_id, lease_hash, input_hash, approval_id,
                    state, leased_at, prepared_at, completed_at, receipt_id
                ) VALUES (
                    :schema, :request_id, :canonical_request_hash, :idempotency_key,
                    :adapter_id, :lease_id, :lease_hash, :input_hash, :approval_id,
                    :state, :leased_at, :prepared_at, :completed_at, :receipt_id
                )
                """,
                candidate.to_record(),
            )
        except sqlite3.IntegrityError as exc:
            by_request = self.get_execution(request.request_id)
            if by_request is not None and by_request == candidate:
                return by_request
            by_key = self.get_by_idempotency(adapter_id, request.idempotency_key)
            if by_key is not None and by_key.request_id != request.request_id:
                raise EffectIdempotencyConflict(
                    "adapter/idempotency key already binds a different request"
                ) from exc
            raise EffectExecutionTransitionError(
                "effect execution persistence failed integrity constraints"
            ) from exc
        return candidate

    def _mark_prepared_in_transaction(
        self, conn: sqlite3.Connection, execution: EffectExecution, *, prepared_at: str
    ) -> EffectExecution:
        if conn is not self._store._conn or not conn.in_transaction:
            raise EffectExecutionTransitionError(
                "execution transition requires the active StateStore transaction"
            )
        current = self.get_execution(execution.request_id)
        if current != execution:
            raise EffectExecutionTransitionError("effect execution changed before prepare")
        if current.state is EffectExecutionState.PREPARED:
            return current
        if current.state is not EffectExecutionState.LEASED:
            raise EffectExecutionTransitionError("only LEASED execution can become PREPARED")
        prepared = EffectExecution.create(
            **{
                **current.to_record(),
                "state": EffectExecutionState.PREPARED,
                "prepared_at": prepared_at,
            }
        )
        cursor = conn.execute(
            """
            UPDATE effect_executions
            SET state = ?, prepared_at = ?
            WHERE request_id = ? AND state = 'LEASED'
            """,
            (prepared.state.value, prepared.prepared_at, prepared.request_id),
        )
        if cursor.rowcount != 1:
            raise EffectExecutionTransitionError("effect execution was not atomically prepared")
        loaded = self.get_execution(prepared.request_id)
        if loaded != prepared:
            raise EffectExecutionTransitionError("durable PREPARED execution does not match transition")
        return prepared

    def _complete_in_transaction(
        self,
        conn: sqlite3.Connection,
        execution: EffectExecution,
        *,
        outcome: EffectOutcome,
        result: Any,
        completed_at: str,
        upstream_reference: str | None = None,
    ) -> tuple[EffectExecution, EffectReceipt]:
        if conn is not self._store._conn or not conn.in_transaction:
            raise EffectExecutionTransitionError(
                "execution completion requires the active StateStore transaction"
            )
        current = self.get_execution(execution.request_id)
        if current is None:
            raise EffectExecutionTransitionError("effect execution disappeared before completion")
        if current.state in (EffectExecutionState.SUCCEEDED, EffectExecutionState.FAILED):
            receipt = self._validate_terminal_receipt(current)
            expected_outcome = (
                EffectOutcome.SUCCEEDED
                if current.state is EffectExecutionState.SUCCEEDED
                else EffectOutcome.FAILED
            )
            candidate_json = canonical_result_json(result)
            if (
                expected_outcome is not outcome
                or receipt.result_json != candidate_json
                or receipt.upstream_reference != upstream_reference
            ):
                raise EffectExecutionTransitionError(
                    "terminal effect execution cannot be overwritten with different outcome material"
                )
            return current, receipt
        if current != execution or current.state is not EffectExecutionState.PREPARED:
            raise EffectExecutionTransitionError("only the current PREPARED execution can complete")

        result_json = canonical_result_json(result)
        result_hash = result_hash_for_json(result_json)
        receipt_id = deterministic_receipt_id(
            request_id=current.request_id,
            adapter_id=current.adapter_id,
            input_hash=current.input_hash,
        )
        receipt = EffectReceipt.create(
            receipt_id=receipt_id,
            request_id=current.request_id,
            canonical_request_hash=current.canonical_request_hash,
            idempotency_key=current.idempotency_key,
            approval_id=current.approval_id,
            adapter_id=current.adapter_id,
            lease_id=current.lease_id,
            input_hash=current.input_hash,
            started_at=current.prepared_at,
            completed_at=completed_at,
            outcome=outcome,
            result_json=result_json,
            result_hash=result_hash,
            upstream_reference=upstream_reference,
        )
        try:
            conn.execute(
                """
                INSERT INTO effect_receipts(
                    schema, receipt_id, request_id, canonical_request_hash,
                    idempotency_key, approval_id, adapter_id, lease_id, input_hash,
                    started_at, completed_at, outcome, result_json, result_hash,
                    upstream_reference
                ) VALUES (
                    :schema, :receipt_id, :request_id, :canonical_request_hash,
                    :idempotency_key, :approval_id, :adapter_id, :lease_id, :input_hash,
                    :started_at, :completed_at, :outcome, :result_json, :result_hash,
                    :upstream_reference
                )
                """,
                receipt.to_record(),
            )
        except sqlite3.IntegrityError as exc:
            existing = self.get_receipt(receipt.receipt_id)
            if existing != receipt:
                raise EffectExecutionTransitionError(
                    "effect receipt identity already binds different terminal material"
                ) from exc

        terminal_state = (
            EffectExecutionState.SUCCEEDED
            if outcome is EffectOutcome.SUCCEEDED
            else EffectExecutionState.FAILED
        )
        terminal = EffectExecution.create(
            **{
                **current.to_record(),
                "state": terminal_state,
                "completed_at": receipt.completed_at,
                "receipt_id": receipt.receipt_id,
            }
        )
        cursor = conn.execute(
            """
            UPDATE effect_executions
            SET state = ?, completed_at = ?, receipt_id = ?
            WHERE request_id = ? AND state = 'PREPARED'
            """,
            (
                terminal.state.value,
                terminal.completed_at,
                terminal.receipt_id,
                terminal.request_id,
            ),
        )
        if cursor.rowcount != 1:
            raise EffectExecutionTransitionError("effect execution was not atomically completed")
        loaded = self.get_execution(terminal.request_id)
        if loaded != terminal:
            raise EffectExecutionTransitionError("durable terminal execution does not match transition")
        loaded_receipt = self._validate_terminal_receipt(terminal)
        if loaded_receipt != receipt:
            raise EffectExecutionTransitionError("durable terminal receipt changed during completion")
        return terminal, receipt
