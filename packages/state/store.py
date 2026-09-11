from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ContextManager, Iterator, Protocol, runtime_checkable


SCHEMA_VERSION = 4


class StateStoreError(RuntimeError):
    """Base error for deterministic state-store failures."""


class UnsupportedSchemaVersion(StateStoreError):
    """Raised when durable state was created by a newer unsupported schema."""


class MigrationIntegrityError(StateStoreError):
    """Raised when the migration ledger and expected schema do not agree."""


@dataclass(frozen=True)
class _Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        material = (
            f"{self.version}\n{self.name}\n" + "\n-- statement --\n".join(self.statements)
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()


_MIGRATIONS: tuple[_Migration, ...] = (
    _Migration(
        version=1,
        name="001_state_store_foundation",
        statements=(
            """
            CREATE TABLE system_state (
                key TEXT PRIMARY KEY NOT NULL CHECK(length(key) > 0),
                value_json TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL
            )
            """,
        ),
    ),
    _Migration(
        version=2,
        name="002_effect_requests",
        statements=(
            """
            CREATE TABLE effect_requests (
                request_id TEXT PRIMARY KEY NOT NULL CHECK(length(request_id) > 0),
                schema TEXT NOT NULL CHECK(length(schema) > 0),
                run_id TEXT NOT NULL CHECK(length(run_id) > 0),
                principal_id TEXT NOT NULL CHECK(length(principal_id) > 0),
                agent_id TEXT NOT NULL CHECK(length(agent_id) > 0),
                action TEXT NOT NULL CHECK(length(action) > 0),
                resource TEXT NOT NULL CHECK(length(resource) > 0),
                arguments_json TEXT NOT NULL,
                idempotency_key TEXT NOT NULL CHECK(length(idempotency_key) > 0),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                canonical_hash TEXT NOT NULL CHECK(length(canonical_hash) = 71)
            )
            """,
            """
            CREATE INDEX effect_requests_idempotency_idx
                ON effect_requests(idempotency_key)
            """,
        ),
    ),
    _Migration(
        version=3,
        name="003_policy_decisions",
        statements=(
            """
            CREATE TABLE policy_decisions (
                decision_id TEXT PRIMARY KEY NOT NULL CHECK(length(decision_id) > 0),
                schema TEXT NOT NULL CHECK(length(schema) > 0),
                request_id TEXT NOT NULL CHECK(length(request_id) > 0),
                decision TEXT NOT NULL CHECK(
                    decision IN ('ALLOW', 'REQUIRE_APPROVAL', 'DENY')
                ),
                policy_revision TEXT NOT NULL CHECK(length(policy_revision) > 0),
                reason_codes_json TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                canonical_request_hash TEXT NOT NULL CHECK(
                    length(canonical_request_hash) = 71
                ),
                FOREIGN KEY(request_id) REFERENCES effect_requests(request_id)
                    ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX policy_decisions_request_idx
                ON policy_decisions(request_id)
            """,
        ),
    ),
    _Migration(
        version=4,
        name="004_approvals",
        statements=(
            """
            CREATE TABLE approvals (
                approval_id TEXT PRIMARY KEY NOT NULL CHECK(length(approval_id) > 0),
                schema TEXT NOT NULL CHECK(length(schema) > 0),
                request_id TEXT NOT NULL CHECK(length(request_id) > 0),
                policy_decision_id TEXT NOT NULL CHECK(length(policy_decision_id) > 0),
                canonical_request_hash TEXT NOT NULL CHECK(
                    length(canonical_request_hash) = 71
                ),
                approver TEXT NOT NULL CHECK(length(approver) > 0),
                decision TEXT NOT NULL CHECK(decision IN ('APPROVE', 'REJECT')),
                scope TEXT NOT NULL CHECK(scope = 'ONCE'),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                FOREIGN KEY(request_id) REFERENCES effect_requests(request_id)
                    ON DELETE RESTRICT,
                FOREIGN KEY(policy_decision_id) REFERENCES policy_decisions(decision_id)
                    ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX approvals_request_idx ON approvals(request_id)
            """,
            """
            CREATE INDEX approvals_policy_decision_idx ON approvals(policy_decision_id)
            """,
        ),
    ),
)


@runtime_checkable
class StateStore(Protocol):
    """Internal persistence boundary used by the controller."""

    @property
    def schema_version(self) -> int:
        ...

    def transaction(self) -> ContextManager[sqlite3.Connection]:
        ...

    def get_system_state(self, key: str, default: Any = None) -> Any:
        ...

    def set_system_state(self, key: str, value: Any) -> None:
        ...

    def delete_system_state(self, key: str) -> bool:
        ...

    def close(self) -> None:
        ...


class SQLiteStateStore:
    """Single-machine durable controller state backed by SQLite WAL."""

    def __init__(self, path: str | os.PathLike[str]):
        raw = os.fspath(path)
        if raw == ":memory:":
            raise StateStoreError("durable StateStore cannot use an in-memory database")

        self.path = Path(raw).expanduser()
        self._closed = False
        self._prepare_parent()

        try:
            self._conn = sqlite3.connect(
                str(self.path), timeout=5.0, isolation_level=None, check_same_thread=True
            )
            self._conn.row_factory = sqlite3.Row
            self._configure_connection()
            self._initialize_schema()
            self._harden_file_permissions()
        except BaseException:
            conn = getattr(self, "_conn", None)
            if conn is not None:
                conn.close()
            self._closed = True
            raise

    def _prepare_parent(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    def _harden_file_permissions(self) -> None:
        if os.name == "posix" and self.path.exists():
            os.chmod(self.path, 0o600)

    def _configure_connection(self) -> None:
        journal_mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(journal_mode).lower() != "wal":
            raise StateStoreError(
                f"SQLite WAL mode required; observed journal_mode={journal_mode!r}"
            )
        self._conn.execute("PRAGMA foreign_keys=ON")
        foreign_keys = self._conn.execute("PRAGMA foreign_keys").fetchone()[0]
        if int(foreign_keys) != 1:
            raise StateStoreError("SQLite foreign_keys enforcement could not be enabled")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA trusted_schema=OFF")

    def _initialize_schema(self) -> None:
        bootstrap = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY NOT NULL,
            name TEXT UNIQUE NOT NULL,
            checksum_sha256 TEXT NOT NULL CHECK(length(checksum_sha256) = 64)
        )
        """
        with self.transaction() as conn:
            conn.execute(bootstrap)
            user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if user_version > SCHEMA_VERSION:
                raise UnsupportedSchemaVersion(
                    f"database schema version {user_version} exceeds supported version {SCHEMA_VERSION}"
                )
            expected = {migration.version: migration for migration in _MIGRATIONS}
            rows = conn.execute(
                "SELECT version, name, checksum_sha256 FROM schema_migrations ORDER BY version"
            ).fetchall()
            recorded_versions = [int(row["version"]) for row in rows]
            if recorded_versions != list(range(1, user_version + 1)):
                raise MigrationIntegrityError(
                    "schema_migrations ledger does not match PRAGMA user_version"
                )
            for row in rows:
                version = int(row["version"])
                migration = expected.get(version)
                if migration is None:
                    raise UnsupportedSchemaVersion(
                        f"migration version {version} is not supported by this build"
                    )
                if row["name"] != migration.name:
                    raise MigrationIntegrityError(
                        f"migration {version} name mismatch: {row['name']!r} != {migration.name!r}"
                    )
                if row["checksum_sha256"] != migration.checksum:
                    raise MigrationIntegrityError(f"migration {version} checksum mismatch")
            for migration in _MIGRATIONS:
                if migration.version <= user_version:
                    continue
                if migration.version != user_version + 1:
                    raise MigrationIntegrityError("migration sequence is not contiguous")
                for statement in migration.statements:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations(version, name, checksum_sha256) VALUES (?, ?, ?)",
                    (migration.version, migration.name, migration.checksum),
                )
                user_version = migration.version
                conn.execute(f"PRAGMA user_version={user_version}")
            if user_version != SCHEMA_VERSION:
                raise MigrationIntegrityError(
                    f"schema initialization ended at {user_version}, expected {SCHEMA_VERSION}"
                )

    def _require_open(self) -> None:
        if self._closed:
            raise StateStoreError("StateStore is closed")

    @property
    def schema_version(self) -> int:
        self._require_open()
        return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    @property
    def journal_mode(self) -> str:
        self._require_open()
        return str(self._conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()

    @property
    def foreign_keys_enabled(self) -> bool:
        self._require_open()
        return bool(int(self._conn.execute("PRAGMA foreign_keys").fetchone()[0]))

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self._require_open()
        if self._conn.in_transaction:
            raise StateStoreError("nested StateStore transactions are not supported")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield self._conn
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str) or not key:
            raise StateStoreError("system_state key must be a non-empty string")

    @staticmethod
    def _encode_json(value: Any) -> str:
        try:
            return json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
        except (TypeError, ValueError) as exc:
            raise StateStoreError("system_state value must be canonical JSON") from exc

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    def get_system_state(self, key: str, default: Any = None) -> Any:
        self._require_open()
        self._validate_key(key)
        row = self._conn.execute("SELECT value_json FROM system_state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value_json"])
        except json.JSONDecodeError as exc:
            raise StateStoreError(f"durable system_state value for {key!r} is invalid JSON") from exc

    def set_system_state(self, key: str, value: Any) -> None:
        self._require_open()
        self._validate_key(key)
        encoded = self._encode_json(value)
        updated_at = self._utc_now()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO system_state(key, value_json, updated_at_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (key, encoded, updated_at),
            )

    def delete_system_state(self, key: str) -> bool:
        self._require_open()
        self._validate_key(key)
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM system_state WHERE key = ?", (key,))
        return cursor.rowcount == 1

    def close(self) -> None:
        if not self._closed:
            self._conn.close()
            self._closed = True

    def __enter__(self) -> "SQLiteStateStore":
        self._require_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
