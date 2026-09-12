from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping

from .store import SQLiteStateStore, StateStoreError


EMERGENCY_PAUSE_SCHEMA = "lac.emergency-pause/v1"
EMERGENCY_PAUSE_STATE_KEY = "controller.emergency_pause"


class EmergencyPauseStateError(StateStoreError):
    """Durable emergency-pause authority is missing, malformed, or unreadable."""


@dataclass(frozen=True)
class EmergencyPauseState:
    """Canonical local emergency-pause authority state."""

    schema: str
    paused: bool

    @classmethod
    def create(cls, *, paused: bool) -> "EmergencyPauseState":
        if not isinstance(paused, bool):
            raise EmergencyPauseStateError("paused must be a boolean")
        return cls(schema=EMERGENCY_PAUSE_SCHEMA, paused=paused)

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "EmergencyPauseState":
        if not isinstance(record, Mapping):
            raise EmergencyPauseStateError("emergency-pause state must be a JSON object")
        required = {"schema", "paused"}
        observed = set(record)
        missing = required - observed
        unknown = observed - required
        if missing or unknown:
            raise EmergencyPauseStateError(
                "invalid emergency-pause fields; "
                f"missing={sorted(missing)} unknown={sorted(unknown)}"
            )
        if record["schema"] != EMERGENCY_PAUSE_SCHEMA:
            raise EmergencyPauseStateError(
                f"unsupported emergency-pause schema: {record['schema']!r}"
            )
        return cls.create(paused=record["paused"])

    def to_record(self) -> dict[str, str | bool]:
        return {"schema": self.schema, "paused": self.paused}


class EmergencyPauseRepository:
    """Narrow durable API for the local emergency pause; never grants dispatch authority."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    @staticmethod
    def _decode_value(value_json: object) -> EmergencyPauseState:
        if not isinstance(value_json, str):
            raise EmergencyPauseStateError(
                "durable emergency-pause value is not encoded as JSON text"
            )
        try:
            value = json.loads(value_json)
        except json.JSONDecodeError as exc:
            raise EmergencyPauseStateError(
                "durable emergency-pause value is invalid JSON"
            ) from exc
        state = EmergencyPauseState.from_record(value)
        canonical = json.dumps(
            state.to_record(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        if canonical != value_json:
            raise EmergencyPauseStateError(
                "durable emergency-pause value is not canonical JSON"
            )
        return state

    def _get_in_transaction(self, conn: sqlite3.Connection) -> EmergencyPauseState:
        if conn is not self._store._conn or not conn.in_transaction:
            raise EmergencyPauseStateError(
                "emergency-pause transaction helper requires the active StateStore transaction"
            )
        try:
            row = conn.execute(
                "SELECT value_json FROM system_state WHERE key = ?",
                (EMERGENCY_PAUSE_STATE_KEY,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise EmergencyPauseStateError(
                "durable emergency-pause authority is unreadable"
            ) from exc
        if row is None:
            raise EmergencyPauseStateError(
                "durable emergency-pause authority is not initialized"
            )
        return self._decode_value(row["value_json"])

    def get(self) -> EmergencyPauseState:
        self._store._require_open()
        try:
            row = self._store._conn.execute(
                "SELECT value_json FROM system_state WHERE key = ?",
                (EMERGENCY_PAUSE_STATE_KEY,),
            ).fetchone()
        except sqlite3.Error as exc:
            raise EmergencyPauseStateError(
                "durable emergency-pause authority is unreadable"
            ) from exc
        if row is None:
            raise EmergencyPauseStateError(
                "durable emergency-pause authority is not initialized"
            )
        return self._decode_value(row["value_json"])

    def _set_paused(self, paused: bool) -> EmergencyPauseState:
        state = EmergencyPauseState.create(paused=paused)
        try:
            with self._store.transaction() as conn:
                existing = conn.execute(
                    "SELECT value_json FROM system_state WHERE key = ?",
                    (EMERGENCY_PAUSE_STATE_KEY,),
                ).fetchone()
                if existing is not None:
                    # Never silently repair malformed authority. An explicit first pause/resume
                    # may initialize an absent record, but corruption remains fail-closed.
                    self._decode_value(existing["value_json"])

                encoded = self._store._encode_json(state.to_record())
                updated_at = self._store._utc_now()
                conn.execute(
                    """
                    INSERT INTO system_state(key, value_json, updated_at_utc)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (EMERGENCY_PAUSE_STATE_KEY, encoded, updated_at),
                )
                loaded = self._get_in_transaction(conn)
                if loaded != state:
                    raise EmergencyPauseStateError(
                        "durable emergency-pause transition did not match the requested state"
                    )
                return loaded
        except EmergencyPauseStateError:
            raise
        except sqlite3.Error as exc:
            raise EmergencyPauseStateError(
                "durable emergency-pause transition failed closed"
            ) from exc

    def pause(self) -> EmergencyPauseState:
        return self._set_paused(True)

    def resume(self) -> EmergencyPauseState:
        return self._set_paused(False)
