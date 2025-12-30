from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ChainIdentity, RelayLog, RelayRoute


class Storage:
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
                CREATE TABLE IF NOT EXISTS identities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    chain_type TEXT NOT NULL,
                    rpc_url TEXT,
                    private_key TEXT,
                    address TEXT,
                    notes TEXT,
                    metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS routes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    source_chain_type TEXT NOT NULL,
                    source_identity_id TEXT NOT NULL,
                    source_adapter TEXT NOT NULL,
                    source_chain_id INTEGER,
                    source_start_block INTEGER,
                    poll_interval INTEGER,
                    dest_chain_type TEXT NOT NULL,
                    dest_identity_id TEXT NOT NULL,
                    dest_adapter TEXT NOT NULL,
                    dest_chain_id INTEGER,
                    metadata TEXT,
                    last_block INTEGER
                );
                CREATE TABLE IF NOT EXISTS relay_logs (
                    id TEXT PRIMARY KEY,
                    route_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail TEXT,
                    created_at REAL NOT NULL
                );
                """
            )

    def _row_to_identity(self, row: sqlite3.Row) -> ChainIdentity:
        return ChainIdentity(
            id=row["id"],
            name=row["name"],
            chain_type=row["chain_type"],
            rpc_url=row["rpc_url"],
            private_key=row["private_key"],
            address=row["address"],
            notes=row["notes"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _row_to_route(self, row: sqlite3.Row) -> RelayRoute:
        return RelayRoute(
            id=row["id"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            source_chain_type=row["source_chain_type"],
            source_identity_id=row["source_identity_id"],
            source_adapter=row["source_adapter"],
            source_chain_id=row["source_chain_id"],
            source_start_block=row["source_start_block"],
            poll_interval=row["poll_interval"] or 5,
            dest_chain_type=row["dest_chain_type"],
            dest_identity_id=row["dest_identity_id"],
            dest_adapter=row["dest_adapter"],
            dest_chain_id=row["dest_chain_id"],
            metadata=json.loads(row["metadata"] or "{}"),
            last_block=row["last_block"],
        )

    # === identities ===
    def add_identity(self, payload: Dict[str, Any]) -> ChainIdentity:
        identity = ChainIdentity(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO identities
                (id, name, chain_type, rpc_url, private_key, address, notes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity.id,
                    identity.name,
                    identity.chain_type,
                    identity.rpc_url,
                    identity.private_key,
                    identity.address,
                    identity.notes,
                    json.dumps(identity.metadata),
                ),
            )
        return identity

    def list_identities(self) -> List[ChainIdentity]:
        rows = self._conn.execute("SELECT * FROM identities").fetchall()
        return [self._row_to_identity(row) for row in rows]

    def get_identity(self, identity_id: str) -> Optional[ChainIdentity]:
        row = self._conn.execute(
            "SELECT * FROM identities WHERE id = ?", (identity_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_identity(row)

    def update_identity(self, identity_id: str, payload: Dict[str, Any]) -> Optional[ChainIdentity]:
        current = self.get_identity(identity_id)
        if not current:
            return None
        data = current.model_dump()
        data.update({k: v for k, v in payload.items() if v is not None})
        identity = ChainIdentity(**data)
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE identities
                SET name=?, chain_type=?, rpc_url=?, private_key=?, address=?, notes=?, metadata=?
                WHERE id=?
                """,
                (
                    identity.name,
                    identity.chain_type,
                    identity.rpc_url,
                    identity.private_key,
                    identity.address,
                    identity.notes,
                    json.dumps(identity.metadata),
                    identity.id,
                ),
            )
        return identity

    def delete_identity(self, identity_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM identities WHERE id = ?", (identity_id,))
        return cur.rowcount > 0

    # === routes ===
    def add_route(self, payload: Dict[str, Any]) -> RelayRoute:
        route = RelayRoute(**payload)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO routes
                (id, name, enabled, source_chain_type, source_identity_id, source_adapter,
                 source_chain_id, source_start_block, poll_interval,
                 dest_chain_type, dest_identity_id, dest_adapter, dest_chain_id,
                 metadata, last_block)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    route.id,
                    route.name,
                    int(route.enabled),
                    route.source_chain_type,
                    route.source_identity_id,
                    route.source_adapter,
                    route.source_chain_id,
                    route.source_start_block,
                    route.poll_interval,
                    route.dest_chain_type,
                    route.dest_identity_id,
                    route.dest_adapter,
                    route.dest_chain_id,
                    json.dumps(route.metadata),
                    route.last_block,
                ),
            )
        return route

    def list_routes(self) -> List[RelayRoute]:
        rows = self._conn.execute("SELECT * FROM routes").fetchall()
        return [self._row_to_route(row) for row in rows]

    def get_route(self, route_id: str) -> Optional[RelayRoute]:
        row = self._conn.execute("SELECT * FROM routes WHERE id = ?", (route_id,)).fetchone()
        if not row:
            return None
        return self._row_to_route(row)

    def update_route(self, route_id: str, payload: Dict[str, Any]) -> Optional[RelayRoute]:
        current = self.get_route(route_id)
        if not current:
            return None
        data = current.model_dump()
        data.update({k: v for k, v in payload.items() if v is not None})
        route = RelayRoute(**data)
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE routes
                SET name=?, enabled=?, source_chain_type=?, source_identity_id=?, source_adapter=?,
                    source_chain_id=?, source_start_block=?, poll_interval=?,
                    dest_chain_type=?, dest_identity_id=?, dest_adapter=?, dest_chain_id=?,
                    metadata=?, last_block=?
                WHERE id=?
                """,
                (
                    route.name,
                    int(route.enabled),
                    route.source_chain_type,
                    route.source_identity_id,
                    route.source_adapter,
                    route.source_chain_id,
                    route.source_start_block,
                    route.poll_interval,
                    route.dest_chain_type,
                    route.dest_identity_id,
                    route.dest_adapter,
                    route.dest_chain_id,
                    json.dumps(route.metadata),
                    route.last_block,
                    route.id,
                ),
            )
        return route

    def update_route_last_block(self, route_id: str, last_block: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE routes SET last_block=? WHERE id=?",
                (last_block, route_id),
            )

    def delete_route(self, route_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM routes WHERE id = ?", (route_id,))
        return cur.rowcount > 0

    # === logs ===
    def add_log(self, route_id: str, message_id: str, direction: str, status: str, detail: Dict[str, Any]) -> RelayLog:
        log = RelayLog(
            route_id=route_id,
            message_id=message_id,
            direction=direction,
            status=status,
            detail=detail,
            created_at=time.time(),
        )
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO relay_logs (id, route_id, message_id, direction, status, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.id,
                    log.route_id,
                    log.message_id,
                    log.direction,
                    log.status,
                    json.dumps(log.detail),
                    log.created_at,
                ),
            )
        return log

    def list_logs(self, route_id: Optional[str] = None, limit: int = 200) -> List[RelayLog]:
        if route_id:
            rows = self._conn.execute(
                "SELECT * FROM relay_logs WHERE route_id = ? ORDER BY created_at DESC LIMIT ?",
                (route_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM relay_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            RelayLog(
                id=row["id"],
                route_id=row["route_id"],
                message_id=row["message_id"],
                direction=row["direction"],
                status=row["status"],
                detail=json.loads(row["detail"] or "{}"),
                created_at=row["created_at"],
            )
            for row in rows
        ]
