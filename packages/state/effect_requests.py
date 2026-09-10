from __future__ import annotations

import sqlite3

from packages.core import EffectRequest, EffectRequestError
from .store import SQLiteStateStore, StateStoreError


class EffectRequestIdentityConflict(StateStoreError):
    """A request_id already exists with different canonical security material."""


class EffectRequestRepository:
    """Durable persistence for canonical effect requests."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    def put(self, request: EffectRequest) -> EffectRequest:
        record = request.to_record()
        try:
            with self._store.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO effect_requests(
                        request_id, schema, run_id, principal_id, agent_id,
                        action, resource, arguments_json, idempotency_key,
                        created_at, expires_at, canonical_hash
                    ) VALUES (
                        :request_id, :schema, :run_id, :principal_id, :agent_id,
                        :action, :resource, :arguments_json, :idempotency_key,
                        :created_at, :expires_at, :canonical_hash
                    )
                    """,
                    record,
                )
        except sqlite3.IntegrityError as exc:
            existing = self.get(request.request_id)
            if existing is None:
                raise StateStoreError(
                    "effect request persistence failed without a readable conflict row"
                ) from exc
            if existing.canonical_hash != request.canonical_hash:
                raise EffectRequestIdentityConflict(
                    f"request_id {request.request_id!r} already binds different canonical security material"
                ) from exc
            return existing
        return request

    def get(self, request_id: str) -> EffectRequest | None:
        if not isinstance(request_id, str) or not request_id:
            raise StateStoreError("request_id must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, request_id, run_id, principal_id, agent_id, action,
                   resource, arguments_json, idempotency_key, created_at,
                   expires_at, canonical_hash
            FROM effect_requests WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            return EffectRequest.from_record(dict(row))
        except EffectRequestError as exc:
            raise StateStoreError(
                f"persisted effect request {request_id!r} failed integrity validation"
            ) from exc
