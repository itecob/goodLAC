from __future__ import annotations

import sqlite3

from packages.core import ExecutionLease, ExecutionLeaseError
from .effect_requests import EffectRequestRepository
from .store import SQLiteStateStore, StateStoreError


class ExecutionLeaseAcquisitionError(StateStoreError):
    """Base error for a lease acquisition that must fail closed."""


class ExecutionLeaseUnavailable(ExecutionLeaseAcquisitionError):
    """Another current unexpired lease already owns the request."""


class ExecutionLeaseIdentityConflict(ExecutionLeaseAcquisitionError):
    """A lease_id already exists with different immutable lease material."""


class ExecutionLeaseBindingError(ExecutionLeaseAcquisitionError):
    """The lease does not bind a readable durable canonical effect request."""


class ExecutionLeaseStateError(ExecutionLeaseAcquisitionError):
    """Persisted lease state is malformed or otherwise untrustworthy."""


class ExecutionLeaseRepository:
    """Transactional durable execution-lease primitive; never authorizes or dispatches."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    @staticmethod
    def _decode(row: sqlite3.Row) -> ExecutionLease:
        try:
            return ExecutionLease.from_record(dict(row))
        except ExecutionLeaseError as exc:
            raise ExecutionLeaseStateError(
                "persisted execution lease failed integrity validation"
            ) from exc

    @staticmethod
    def _validate_nonoverlapping(leases: list[ExecutionLease]) -> None:
        ordered = sorted(leases, key=lambda item: (item.issued_at, item.lease_id))
        for previous, current in zip(ordered, ordered[1:]):
            if current.issued_at < previous.expires_at:
                raise ExecutionLeaseStateError(
                    "persisted execution leases overlap for one request"
                )

    @staticmethod
    def _rows_for_request(conn: sqlite3.Connection, request_id: str) -> list[ExecutionLease]:
        rows = conn.execute(
            """
            SELECT schema, lease_id, request_id, executor_id, issued_at, expires_at
            FROM execution_leases
            WHERE request_id = ?
            ORDER BY issued_at, lease_id
            """,
            (request_id,),
        ).fetchall()
        leases = [ExecutionLeaseRepository._decode(row) for row in rows]
        ExecutionLeaseRepository._validate_nonoverlapping(leases)
        return leases

    def _acquire_in_transaction(
        self, conn: sqlite3.Connection, lease: ExecutionLease
    ) -> ExecutionLease:
        if conn is not self._store._conn or not conn.in_transaction:
            raise ExecutionLeaseAcquisitionError(
                "execution lease acquisition requires the active StateStore transaction"
            )
        if not isinstance(lease, ExecutionLease):
            raise ExecutionLeaseAcquisitionError(
                "lease must be a canonical ExecutionLease"
            )
        try:
            canonical = ExecutionLease.from_record(lease.to_record())
        except (ExecutionLeaseError, TypeError, AttributeError) as exc:
            raise ExecutionLeaseAcquisitionError(
                "lease failed canonical integrity validation"
            ) from exc
        if canonical != lease:
            raise ExecutionLeaseAcquisitionError("lease is not canonical")

        try:
            request = EffectRequestRepository(self._store).get(lease.request_id)
        except StateStoreError as exc:
            raise ExecutionLeaseBindingError(
                "durable request failed integrity validation"
            ) from exc
        if request is None:
            raise ExecutionLeaseBindingError(
                f"request_id {lease.request_id!r} is not durably persisted"
            )

        identity_row = conn.execute(
            """
            SELECT schema, lease_id, request_id, executor_id, issued_at, expires_at
            FROM execution_leases WHERE lease_id = ?
            """,
            (lease.lease_id,),
        ).fetchone()
        existing_identity = None
        if identity_row is not None:
            existing_identity = self._decode(identity_row)
            if existing_identity != lease:
                raise ExecutionLeaseIdentityConflict(
                    f"lease_id {lease.lease_id!r} already binds different material"
                )

        existing_leases = self._rows_for_request(conn, lease.request_id)
        if existing_identity is not None:
            return existing_identity

        for existing in existing_leases:
            try:
                expired = existing.is_expired(lease.issued_at)
            except ExecutionLeaseError as exc:
                raise ExecutionLeaseStateError(
                    "persisted execution lease expiry could not be evaluated"
                ) from exc
            if not expired:
                raise ExecutionLeaseUnavailable(
                    "request already has a current unexpired execution lease"
                )

        try:
            conn.execute(
                """
                INSERT INTO execution_leases(
                    lease_id, schema, request_id, executor_id, issued_at, expires_at
                ) VALUES (
                    :lease_id, :schema, :request_id, :executor_id, :issued_at, :expires_at
                )
                """,
                lease.to_record(),
            )
        except sqlite3.IntegrityError as exc:
            raise ExecutionLeaseAcquisitionError(
                "execution lease persistence failed integrity constraints"
            ) from exc
        return lease

    def acquire(self, lease: ExecutionLease) -> ExecutionLease:
        with self._store.transaction() as conn:
            return self._acquire_in_transaction(conn, lease)

    def get(self, lease_id: str) -> ExecutionLease | None:
        if not isinstance(lease_id, str) or not lease_id:
            raise StateStoreError("lease_id must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, lease_id, request_id, executor_id, issued_at, expires_at
            FROM execution_leases WHERE lease_id = ?
            """,
            (lease_id,),
        ).fetchone()
        if row is None:
            return None
        lease = self._decode(row)
        self._validate_nonoverlapping(
            self._rows_for_request(self._store._conn, lease.request_id)
        )
        try:
            request = EffectRequestRepository(self._store).get(lease.request_id)
        except StateStoreError as exc:
            raise ExecutionLeaseBindingError(
                f"persisted execution lease {lease_id!r} lost readable request binding"
            ) from exc
        if request is None:
            raise ExecutionLeaseBindingError(
                f"persisted execution lease {lease_id!r} lost request binding"
            )
        return lease
