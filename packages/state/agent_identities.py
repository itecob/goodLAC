from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .store import SQLiteStateStore, StateStoreError


AGENT_IDENTITY_SCHEMA = "lac.agent-identity/v1"
AGENT_IDENTITY_KEY_PREFIX = "controller.agent_identity:"


class AgentIdentityStateError(StateStoreError):
    """Durable agent identity state is missing, malformed, or inconsistent."""


class AgentIdentityConflict(AgentIdentityStateError):
    """An agent identity already exists with different immutable material."""


class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AgentIdentityStateError(f"{field} must be a non-empty trimmed string")
    return value


@dataclass(frozen=True)
class AgentIdentity:
    schema: str
    agent_id: str
    principal_id: str
    status: AgentStatus

    @classmethod
    def create(
        cls,
        *,
        agent_id: str,
        principal_id: str,
        status: AgentStatus | str = AgentStatus.ACTIVE,
        schema: str = AGENT_IDENTITY_SCHEMA,
    ) -> "AgentIdentity":
        if schema != AGENT_IDENTITY_SCHEMA:
            raise AgentIdentityStateError(f"unsupported agent identity schema: {schema!r}")
        try:
            normalized_status = status if isinstance(status, AgentStatus) else AgentStatus(status)
        except (TypeError, ValueError) as exc:
            raise AgentIdentityStateError("unknown agent identity status") from exc
        return cls(
            schema=schema,
            agent_id=_required_text(agent_id, "agent_id"),
            principal_id=_required_text(principal_id, "principal_id"),
            status=normalized_status,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "AgentIdentity":
        if set(record) != {"schema", "agent_id", "principal_id", "status"}:
            raise AgentIdentityStateError("invalid persisted agent identity fields")
        return cls.create(**dict(record))

    def to_record(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "agent_id": self.agent_id,
            "principal_id": self.principal_id,
            "status": self.status.value,
        }


class AgentIdentityRepository:
    """Controller-owned durable agent identity and revocation state."""

    def __init__(self, store: SQLiteStateStore):
        if not isinstance(store, SQLiteStateStore):
            raise AgentIdentityStateError("store must be a SQLiteStateStore")
        self._store = store

    @staticmethod
    def _key(agent_id: str) -> str:
        return AGENT_IDENTITY_KEY_PREFIX + _required_text(agent_id, "agent_id")

    @staticmethod
    def _decode(value_json: str, expected_agent_id: str) -> AgentIdentity:
        try:
            raw = json.loads(value_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AgentIdentityStateError("persisted agent identity is invalid JSON") from exc
        if not isinstance(raw, dict):
            raise AgentIdentityStateError("persisted agent identity must be a JSON object")
        identity = AgentIdentity.from_record(raw)
        if identity.agent_id != expected_agent_id:
            raise AgentIdentityStateError("persisted agent identity key/id binding is inconsistent")
        return identity

    def _get_in_transaction(
        self, conn: sqlite3.Connection, agent_id: str
    ) -> AgentIdentity | None:
        if conn is not self._store._conn or not conn.in_transaction:
            raise AgentIdentityStateError(
                "agent identity mutation requires the active StateStore transaction"
            )
        normalized_agent = _required_text(agent_id, "agent_id")
        row = conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?",
            (self._key(normalized_agent),),
        ).fetchone()
        if row is None:
            return None
        return self._decode(row["value_json"], normalized_agent)

    def get(self, agent_id: str) -> AgentIdentity | None:
        normalized_agent = _required_text(agent_id, "agent_id")
        row = self._store._conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?",
            (self._key(normalized_agent),),
        ).fetchone()
        if row is None:
            return None
        return self._decode(row["value_json"], normalized_agent)

    def _put_in_transaction(
        self, conn: sqlite3.Connection, identity: AgentIdentity
    ) -> AgentIdentity:
        if conn is not self._store._conn or not conn.in_transaction:
            raise AgentIdentityStateError(
                "agent identity mutation requires the active StateStore transaction"
            )
        if not isinstance(identity, AgentIdentity):
            raise AgentIdentityStateError("identity must be an AgentIdentity")
        encoded = self._store._encode_json(identity.to_record())
        conn.execute(
            """
            INSERT INTO system_state(key, value_json, updated_at_utc)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at_utc = excluded.updated_at_utc
            """,
            (self._key(identity.agent_id), encoded, self._store._utc_now()),
        )
        loaded = self._get_in_transaction(conn, identity.agent_id)
        if loaded != identity:
            raise AgentIdentityStateError("durable agent identity changed during mutation")
        return loaded

    def register_active(self, agent_id: str, principal_id: str) -> AgentIdentity:
        candidate = AgentIdentity.create(
            agent_id=agent_id,
            principal_id=principal_id,
            status=AgentStatus.ACTIVE,
        )
        with self._store.transaction() as conn:
            current = self._get_in_transaction(conn, candidate.agent_id)
            if current is None:
                return self._put_in_transaction(conn, candidate)
            if current != candidate:
                raise AgentIdentityConflict(
                    "agent identity already exists with different principal or status"
                )
            return current

    def _set_status(self, agent_id: str, status: AgentStatus) -> AgentIdentity:
        with self._store.transaction() as conn:
            current = self._get_in_transaction(conn, agent_id)
            if current is None:
                raise AgentIdentityStateError("cannot change status of unknown durable agent identity")
            candidate = AgentIdentity.create(
                agent_id=current.agent_id,
                principal_id=current.principal_id,
                status=status,
            )
            if current == candidate:
                return current
            return self._put_in_transaction(conn, candidate)

    def revoke(self, agent_id: str) -> AgentIdentity:
        return self._set_status(agent_id, AgentStatus.REVOKED)

    def activate(self, agent_id: str) -> AgentIdentity:
        return self._set_status(agent_id, AgentStatus.ACTIVE)
