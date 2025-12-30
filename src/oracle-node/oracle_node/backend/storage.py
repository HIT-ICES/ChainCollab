from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from .models import (
    ChainIdentity,
    ComputeTaskLog,
    ComputeWatcher,
    ContractInterface,
    DataSource,
    EventLog,
    EventSpec,
)


class Storage:
    """SQLite 存储，便于后续迁移到 PostgreSQL。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS data_sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS contracts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    chain_type TEXT NOT NULL,
                    address TEXT,
                    abi TEXT,
                    description TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    chain_type TEXT NOT NULL,
                    contract_interface_id TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    filter_args TEXT,
                    rpc_url TEXT,
                    start_block INTEGER,
                    poll_interval INTEGER,
                    confirmations INTEGER,
                    callback_url TEXT
                );
                CREATE TABLE IF NOT EXISTS event_logs (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS identities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    chain_type TEXT NOT NULL,
                    rpc_url TEXT NOT NULL,
                    private_key TEXT NOT NULL,
                    address TEXT,
                    notes TEXT,
                    metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS compute_watchers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    chain_type TEXT NOT NULL,
                    contract_address TEXT NOT NULL,
                    identity_id TEXT NOT NULL,
                    poll_interval INTEGER,
                    compute_profiles TEXT,
                    enabled INTEGER
                );
                CREATE TABLE IF NOT EXISTS compute_logs (
                    id TEXT PRIMARY KEY,
                    watcher_id TEXT NOT NULL,
                    task_id INTEGER NOT NULL,
                    compute_type TEXT,
                    payload_hash TEXT,
                    result TEXT,
                    tx_hash TEXT,
                    status TEXT,
                    error TEXT
                );
                """
            )
        self._ensure_identity_schema()

    def _ensure_identity_schema(self) -> None:
        cols = {
            row["name"]: row
            for row in self._conn.execute("PRAGMA table_info(identities)").fetchall()
        }
        if "metadata" not in cols:
            with self._conn:
                self._conn.execute("ALTER TABLE identities ADD COLUMN metadata TEXT")

    def _normalize_identity_row(self, row: sqlite3.Row) -> ChainIdentity:
        rpc_url = row["rpc_url"] or None
        private_key = row["private_key"] or None
        return ChainIdentity(
            id=row["id"],
            name=row["name"],
            chain_type=row["chain_type"],
            rpc_url=rpc_url,
            private_key=private_key,
            address=row["address"],
            notes=row["notes"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _prepare_identity(self, identity: ChainIdentity) -> tuple:
        rpc_url = identity.rpc_url or ""
        private_key = identity.private_key or ""
        return (
            identity.id,
            identity.name,
            identity.chain_type,
            rpc_url,
            private_key,
            identity.address,
            identity.notes,
            json.dumps(identity.metadata),
        )

    # ======== DataSource ========
    def add_data_source(self, payload: dict) -> DataSource:
        ds = DataSource(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO data_sources (id, name, type, endpoint, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ds.id,
                    ds.name,
                    ds.type,
                    ds.endpoint,
                    ds.description,
                    json.dumps(ds.metadata),
                ),
            )
        return ds

    def list_data_sources(self) -> List[DataSource]:
        rows = self._conn.execute("SELECT * FROM data_sources").fetchall()
        return [
            DataSource(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                endpoint=row["endpoint"],
                description=row["description"],
                metadata=json.loads(row["metadata"] or "{}"),
            )
            for row in rows
        ]

    # ======== ContractInterface ========
    def add_contract(self, payload: dict) -> ContractInterface:
        iface = ContractInterface(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO contracts (id, name, chain_type, address, abi, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    iface.id,
                    iface.name,
                    iface.chain_type,
                    iface.address,
                    json.dumps(iface.abi) if iface.abi is not None else None,
                    iface.description,
                ),
            )
        return iface

    def list_contracts(self) -> List[ContractInterface]:
        rows = self._conn.execute("SELECT * FROM contracts").fetchall()
        return [
            ContractInterface(
                id=row["id"],
                name=row["name"],
                chain_type=row["chain_type"],
                address=row["address"],
                abi=json.loads(row["abi"]) if row["abi"] else None,
                description=row["description"],
            )
            for row in rows
        ]

    def get_contract(self, iface_id: str) -> Optional[ContractInterface]:
        row = self._conn.execute(
            "SELECT * FROM contracts WHERE id = ?", (iface_id,)
        ).fetchone()
        if not row:
            return None
        return ContractInterface(
            id=row["id"],
            name=row["name"],
            chain_type=row["chain_type"],
            address=row["address"],
            abi=json.loads(row["abi"]) if row["abi"] else None,
            description=row["description"],
        )

    # ======== Events ========
    def add_event(self, payload: dict) -> EventSpec:
        event = EventSpec(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO events (
                    id, name, chain_type, contract_interface_id, event_name,
                    filter_args, rpc_url, start_block, poll_interval, confirmations, callback_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.name,
                    event.chain_type,
                    event.contract_interface_id,
                    event.event_name,
                    json.dumps(event.filter_args),
                    event.rpc_url,
                    event.start_block,
                    event.poll_interval,
                    event.confirmations,
                    event.callback_url,
                ),
            )
        return event

    def list_events(self) -> List[EventSpec]:
        rows = self._conn.execute("SELECT * FROM events").fetchall()
        return [
            EventSpec(
                id=row["id"],
                name=row["name"],
                chain_type=row["chain_type"],
                contract_interface_id=row["contract_interface_id"],
                event_name=row["event_name"],
                filter_args=json.loads(row["filter_args"] or "{}"),
                rpc_url=row["rpc_url"],
                start_block=row["start_block"],
                poll_interval=row["poll_interval"],
                confirmations=row["confirmations"],
                callback_url=row["callback_url"],
            )
            for row in rows
        ]

    def get_event(self, event_id: str) -> Optional[EventSpec]:
        row = self._conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            return None
        return EventSpec(
            id=row["id"],
            name=row["name"],
            chain_type=row["chain_type"],
            contract_interface_id=row["contract_interface_id"],
            event_name=row["event_name"],
            filter_args=json.loads(row["filter_args"] or "{}"),
            rpc_url=row["rpc_url"],
            start_block=row["start_block"],
            poll_interval=row["poll_interval"],
            confirmations=row["confirmations"],
            callback_url=row["callback_url"],
        )

    def append_event_log(self, payload: dict) -> EventLog:
        log = EventLog(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO event_logs (id, event_id, payload) VALUES (?, ?, ?)",
                (log.id, log.event_id, json.dumps(log.payload)),
            )
        return log

    def list_event_logs(self, event_id: Optional[str] = None) -> List[EventLog]:
        if event_id:
            rows = self._conn.execute(
                "SELECT * FROM event_logs WHERE event_id = ?", (event_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM event_logs").fetchall()
        return [
            EventLog(id=row["id"], event_id=row["event_id"], payload=json.loads(row["payload"]))
            for row in rows
        ]

    # ======== Chain identities ========
    def add_identity(self, payload: dict) -> ChainIdentity:
        identity = ChainIdentity(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO identities (id, name, chain_type, rpc_url, private_key, address, notes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._prepare_identity(identity),
            )
        return identity

    def list_identities(self) -> List[ChainIdentity]:
        rows = self._conn.execute("SELECT * FROM identities").fetchall()
        return [self._normalize_identity_row(row) for row in rows]

    def get_identity(self, identity_id: str) -> Optional[ChainIdentity]:
        row = self._conn.execute(
            "SELECT * FROM identities WHERE id = ?", (identity_id,)
        ).fetchone()
        if not row:
            return None
        return self._normalize_identity_row(row)

    def get_identity_by_name(self, name: str) -> Optional[ChainIdentity]:
        row = self._conn.execute(
            "SELECT * FROM identities WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return None
        return self._normalize_identity_row(row)

    def update_identity(self, identity_id: str, payload: dict) -> Optional[ChainIdentity]:
        existing = self.get_identity(identity_id)
        if not existing:
            return None
        data = existing.model_dump()
        for key, value in payload.items():
            if key == "metadata":
                data["metadata"] = value if value is not None else {}
                continue
            if value is not None:
                data[key] = value
        identity = ChainIdentity(**data)
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE identities
                SET name = ?, chain_type = ?, rpc_url = ?, private_key = ?, address = ?, notes = ?, metadata = ?
                WHERE id = ?
                """,
                (
                    identity.name,
                    identity.chain_type,
                    identity.rpc_url or "",
                    identity.private_key or "",
                    identity.address,
                    identity.notes,
                    json.dumps(identity.metadata),
                    identity_id,
                ),
            )
        return identity

    def delete_identity(self, identity_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM identities WHERE id = ?",
                (identity_id,),
            )
        return cur.rowcount > 0

    # ======== Compute watchers ========
    def add_compute_watcher(self, payload: dict) -> ComputeWatcher:
        watcher = ComputeWatcher(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO compute_watchers (
                    id, name, chain_type, contract_address, identity_id,
                    poll_interval, compute_profiles, enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    watcher.id,
                    watcher.name,
                    watcher.chain_type,
                    watcher.contract_address,
                    watcher.identity_id,
                    watcher.poll_interval,
                    json.dumps(watcher.compute_profiles),
                    1 if watcher.enabled else 0,
                ),
            )
        return watcher

    def list_compute_watchers(self) -> List[ComputeWatcher]:
        rows = self._conn.execute("SELECT * FROM compute_watchers").fetchall()
        return [
            ComputeWatcher(
                id=row["id"],
                name=row["name"],
                chain_type=row["chain_type"],
                contract_address=row["contract_address"],
                identity_id=row["identity_id"],
                poll_interval=row["poll_interval"],
                compute_profiles=json.loads(row["compute_profiles"] or "{}"),
                enabled=bool(row["enabled"]),
            )
            for row in rows
        ]

    def get_compute_watcher(self, watcher_id: str) -> Optional[ComputeWatcher]:
        row = self._conn.execute(
            "SELECT * FROM compute_watchers WHERE id = ?", (watcher_id,)
        ).fetchone()
        if not row:
            return None
        return ComputeWatcher(
            id=row["id"],
            name=row["name"],
            chain_type=row["chain_type"],
            contract_address=row["contract_address"],
            identity_id=row["identity_id"],
            poll_interval=row["poll_interval"],
            compute_profiles=json.loads(row["compute_profiles"] or "{}"),
            enabled=bool(row["enabled"]),
        )

    def get_compute_watcher_by_name(self, name: str) -> Optional[ComputeWatcher]:
        row = self._conn.execute(
            "SELECT * FROM compute_watchers WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return None
        return ComputeWatcher(
            id=row["id"],
            name=row["name"],
            chain_type=row["chain_type"],
            contract_address=row["contract_address"],
            identity_id=row["identity_id"],
            poll_interval=row["poll_interval"],
            compute_profiles=json.loads(row["compute_profiles"] or "{}"),
            enabled=bool(row["enabled"]),
        )

    def set_compute_watcher_enabled(self, watcher_id: str, enabled: bool) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE compute_watchers SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, watcher_id),
            )

    def append_compute_log(self, payload: dict) -> ComputeTaskLog:
        log = ComputeTaskLog(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO compute_logs (
                    id, watcher_id, task_id, compute_type, payload_hash, result,
                    tx_hash, status, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.id,
                    log.watcher_id,
                    log.task_id,
                    log.compute_type,
                    log.payload_hash,
                    log.result,
                    log.tx_hash,
                    log.status,
                    log.error,
                ),
            )
        return log

    def list_compute_logs(self, watcher_id: Optional[str] = None) -> List[ComputeTaskLog]:
        if watcher_id:
            rows = self._conn.execute(
                "SELECT * FROM compute_logs WHERE watcher_id = ?", (watcher_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM compute_logs").fetchall()
        return [
            ComputeTaskLog(
                id=row["id"],
                watcher_id=row["watcher_id"],
                task_id=row["task_id"],
                compute_type=row["compute_type"],
                payload_hash=row["payload_hash"],
                result=row["result"],
                tx_hash=row["tx_hash"],
                status=row["status"],
                error=row["error"],
            )
            for row in rows
        ]
