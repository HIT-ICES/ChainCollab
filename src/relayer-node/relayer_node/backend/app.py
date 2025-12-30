from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import ChainIdentity, RelayLog, RelayRoute
from .relayer import RelayerManager
from .storage import Storage


BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "relayer_state.db"
storage = Storage(STATE_PATH)
relayer_manager = RelayerManager(storage)

app = FastAPI(title="Relayer Node Control Plane", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IdentityIn(BaseModel):
    name: str
    chain_type: str
    rpc_url: Optional[str] = None
    private_key: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IdentityUpdate(BaseModel):
    name: Optional[str] = None
    chain_type: Optional[str] = None
    rpc_url: Optional[str] = None
    private_key: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RouteIn(BaseModel):
    name: str
    enabled: bool = True
    source_chain_type: str
    source_identity_id: str
    source_adapter: str
    source_chain_id: Optional[int] = None
    source_start_block: Optional[int] = None
    poll_interval: int = 5
    dest_chain_type: str
    dest_identity_id: str
    dest_adapter: str
    dest_chain_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    source_chain_type: Optional[str] = None
    source_identity_id: Optional[str] = None
    source_adapter: Optional[str] = None
    source_chain_id: Optional[int] = None
    source_start_block: Optional[int] = None
    poll_interval: Optional[int] = None
    dest_chain_type: Optional[str] = None
    dest_identity_id: Optional[str] = None
    dest_adapter: Optional[str] = None
    dest_chain_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    last_block: Optional[int] = None


@app.on_event("startup")
def _on_startup() -> None:
    relayer_manager.start()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/control/status")
def control_status() -> Dict[str, Any]:
    return {"running": relayer_manager._thread is not None and relayer_manager._thread.is_alive()}


@app.post("/control/start")
def control_start() -> Dict[str, str]:
    relayer_manager.start()
    return {"status": "started"}


@app.post("/control/stop")
def control_stop() -> Dict[str, str]:
    relayer_manager.stop()
    return {"status": "stopped"}


@app.get("/identities", response_model=List[ChainIdentity])
def list_identities() -> List[ChainIdentity]:
    return storage.list_identities()


@app.post("/identities", response_model=ChainIdentity)
def add_identity(payload: IdentityIn) -> ChainIdentity:
    data = payload.model_dump()
    if data.get("metadata") is None:
        data["metadata"] = {}
    return storage.add_identity(data)


@app.get("/identities/{identity_id}", response_model=ChainIdentity)
def get_identity(identity_id: str) -> ChainIdentity:
    identity = storage.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="identity not found")
    return identity


@app.put("/identities/{identity_id}", response_model=ChainIdentity)
def update_identity(identity_id: str, payload: IdentityUpdate) -> ChainIdentity:
    identity = storage.update_identity(identity_id, payload.model_dump(exclude_unset=True))
    if not identity:
        raise HTTPException(status_code=404, detail="identity not found")
    return identity


@app.delete("/identities/{identity_id}")
def delete_identity(identity_id: str) -> Dict[str, str]:
    ok = storage.delete_identity(identity_id)
    if not ok:
        raise HTTPException(status_code=404, detail="identity not found")
    return {"status": "deleted"}


@app.get("/routes", response_model=List[RelayRoute])
def list_routes() -> List[RelayRoute]:
    return storage.list_routes()


@app.post("/routes", response_model=RelayRoute)
def add_route(payload: RouteIn) -> RelayRoute:
    data = payload.model_dump()
    if data.get("metadata") is None:
        data["metadata"] = {}
    return storage.add_route(data)


@app.get("/routes/{route_id}", response_model=RelayRoute)
def get_route(route_id: str) -> RelayRoute:
    route = storage.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="route not found")
    return route


@app.put("/routes/{route_id}", response_model=RelayRoute)
def update_route(route_id: str, payload: RouteUpdate) -> RelayRoute:
    route = storage.update_route(route_id, payload.model_dump(exclude_unset=True))
    if not route:
        raise HTTPException(status_code=404, detail="route not found")
    return route


@app.delete("/routes/{route_id}")
def delete_route(route_id: str) -> Dict[str, str]:
    ok = storage.delete_route(route_id)
    if not ok:
        raise HTTPException(status_code=404, detail="route not found")
    return {"status": "deleted"}


@app.get("/logs", response_model=List[RelayLog])
def list_logs(route_id: Optional[str] = None, limit: int = 200) -> List[RelayLog]:
    return storage.list_logs(route_id=route_id, limit=limit)
