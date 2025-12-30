from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, PlainTextResponse
from eth_account import Account
from pydantic import BaseModel
import yaml
import json

from .compute_watcher import ComputeWatcherManager
from .event_listener import EventManager
from .models import ChainIdentity, ComputeWatcher, ContractInterface, DataSource, EventSpec
from .storage import Storage


BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "oracle_state.db"
CONTRACTS_DIR = BASE_DIR.parent / "contracts" / "solidity"
BYTECODE_BIN = CONTRACTS_DIR / "UnifiedOracle.bytecode.bin"
BYTECODE_META = CONTRACTS_DIR / "UnifiedOracle.bytecode.meta.json"
LOCAL_CHAIN_DIR = BASE_DIR.parent / "local-chain"
storage = Storage(STATE_PATH)
event_manager = EventManager(storage)
compute_manager = ComputeWatcherManager(storage)

app = FastAPI(title="Oracle 控制平面", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Pydantic 输入模型 ===


class DataSourceIn(BaseModel):
    name: str
    type: str
    endpoint: str
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ContractIn(BaseModel):
    name: str
    chain_type: str
    address: Optional[str] = None
    abi: Optional[list] = None
    description: Optional[str] = None


class EventIn(BaseModel):
    name: str
    chain_type: str
    contract_interface_id: str
    event_name: str
    filter_args: Optional[dict] = None
    rpc_url: Optional[str] = None
    start_block: Optional[int] = None
    poll_interval: int = 5
    confirmations: int = 0
    callback_url: Optional[str] = None


class ComputeWatcherIn(BaseModel):
    name: str
    chain_type: str
    contract_address: str
    identity_id: str
    poll_interval: int = 5
    compute_profiles: Optional[dict] = None
    enabled: bool = False


class ChainIdentityIn(BaseModel):
    name: str
    chain_type: str
    rpc_url: Optional[str] = None
    private_key: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


class ChainIdentityUpdate(BaseModel):
    name: Optional[str] = None
    chain_type: Optional[str] = None
    rpc_url: Optional[str] = None
    private_key: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict] = None


# === API ===


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/data-sources", response_model=DataSource)
def add_data_source(payload: DataSourceIn) -> DataSource:
    data = payload.model_dump()
    if data.get("metadata") is None:
        data["metadata"] = {}
    ds = storage.add_data_source(data)
    return ds


@app.get("/data-sources", response_model=List[DataSource])
def list_data_sources() -> List[DataSource]:
    return storage.list_data_sources()


@app.post("/identities", response_model=ChainIdentity)
def add_identity(payload: ChainIdentityIn) -> ChainIdentity:
    data = payload.model_dump()
    if data.get("metadata") is None:
        data["metadata"] = {}
    if data.get("chain_type") == "evm":
        if not data.get("rpc_url") or not data.get("private_key"):
            raise HTTPException(
                status_code=400, detail="evm identity requires rpc_url and private_key"
            )
        if not data.get("address"):
            try:
                data["address"] = Account.from_key(data["private_key"]).address
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"invalid private_key: {exc}") from exc
    return storage.add_identity(data)


@app.get("/identities", response_model=List[ChainIdentity])
def list_identities() -> List[ChainIdentity]:
    return storage.list_identities()


@app.get("/identities/{identity_id}", response_model=ChainIdentity)
def get_identity(identity_id: str) -> ChainIdentity:
    identity = storage.get_identity(identity_id)
    if not identity:
        raise HTTPException(status_code=404, detail="identity not found")
    return identity


@app.put("/identities/{identity_id}", response_model=ChainIdentity)
def update_identity(identity_id: str, payload: ChainIdentityUpdate) -> ChainIdentity:
    existing = storage.get_identity(identity_id)
    if not existing:
        raise HTTPException(status_code=404, detail="identity not found")
    data = payload.model_dump()
    chain_type = data.get("chain_type") or existing.chain_type
    if chain_type == "evm":
        rpc_url = data.get("rpc_url") if data.get("rpc_url") is not None else existing.rpc_url
        private_key = (
            data.get("private_key") if data.get("private_key") is not None else existing.private_key
        )
        if not rpc_url or not private_key:
            raise HTTPException(status_code=400, detail="evm identity requires rpc_url and private_key")
        if not (data.get("address") or existing.address):
            try:
                data["address"] = Account.from_key(private_key).address
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"invalid private_key: {exc}") from exc
    updated = storage.update_identity(identity_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="identity not found")
    return updated


@app.delete("/identities/{identity_id}")
def delete_identity(identity_id: str) -> dict:
    deleted = storage.delete_identity(identity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="identity not found")
    return {"status": "deleted", "identity_id": identity_id}


@app.post("/contracts", response_model=ContractInterface)
def add_contract(payload: ContractIn) -> ContractInterface:
    return storage.add_contract(payload.model_dump())


@app.get("/contracts", response_model=List[ContractInterface])
def list_contracts() -> List[ContractInterface]:
    return storage.list_contracts()


@app.get("/contracts/unified/sol")
def get_unified_contract_source() -> PlainTextResponse:
    path = CONTRACTS_DIR / "UnifiedOracle.sol"
    if not path.exists():
        raise HTTPException(status_code=404, detail="UnifiedOracle.sol not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.get("/contracts/unified/abi")
def get_unified_contract_abi() -> JSONResponse:
    path = CONTRACTS_DIR / "UnifiedOracle.abi.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="UnifiedOracle ABI not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    return JSONResponse(content=data)


@app.get("/contracts/unified/bytecode")
def get_unified_contract_bytecode() -> JSONResponse:
    sol_path = CONTRACTS_DIR / "UnifiedOracle.sol"
    if not sol_path.exists():
        raise HTTPException(status_code=404, detail="UnifiedOracle.sol not found")
    if BYTECODE_BIN.exists():
        bytecode = BYTECODE_BIN.read_text(encoding="utf-8").strip()
        if bytecode:
            if not bytecode.startswith("0x"):
                bytecode = f"0x{bytecode}"
            return JSONResponse(content={"bytecode": bytecode, "cached": True})
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    "solc",
                    "--bin",
                    "-o",
                    tmp_dir,
                    str(sol_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            _ = result  # keep for debugging if needed
            bin_path = Path(tmp_dir) / "UnifiedOracle.bin"
            if not bin_path.exists():
                bins = list(Path(tmp_dir).glob("*.bin"))
                if not bins:
                    raise HTTPException(status_code=500, detail="bytecode not generated")
                bin_path = bins[0]
            bytecode = bin_path.read_text(encoding="utf-8").strip()
            if not bytecode:
                raise HTTPException(status_code=500, detail="empty bytecode")
            if not bytecode.startswith("0x"):
                bytecode = f"0x{bytecode}"
            BYTECODE_BIN.write_text(bytecode, encoding="utf-8")
            BYTECODE_META.write_text(
                json.dumps(
                    {
                        "source_mtime": sol_path.stat().st_mtime,
                        "compiled_at": time.time(),
                    }
                ),
                encoding="utf-8",
            )
            return JSONResponse(content={"bytecode": bytecode})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="solc not found. Install solc to compile.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="solc compile timed out") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or "solc compilation failed"
        raise HTTPException(status_code=500, detail=detail) from exc


def _load_local_chain_config() -> dict:
    path = LOCAL_CHAIN_DIR / "chain_config.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="local chain config not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    mnemonic_path = LOCAL_CHAIN_DIR / "mnemonic.txt"
    if mnemonic_path.exists() and not data.get("mnemonic"):
        data["mnemonic"] = mnemonic_path.read_text(encoding="utf-8").strip()
    return data


@app.get("/local-chain/config")
def get_local_chain_config() -> dict:
    return _load_local_chain_config()


@app.get("/local-chain/accounts")
def get_local_chain_accounts() -> dict:
    accounts_path = LOCAL_CHAIN_DIR / "accounts.json"
    if accounts_path.exists():
        return json.loads(accounts_path.read_text(encoding="utf-8"))
    cfg = _load_local_chain_config()
    mnemonic = cfg.get("mnemonic")
    if not mnemonic:
        raise HTTPException(status_code=400, detail="mnemonic missing in config")
    try:
        Account.enable_unaudited_hdwallet_features()
        account_count = int(cfg.get("account_count", 10))
        base_path = cfg.get("derivation_path", "m/44'/60'/0'/0")
        accounts = []
        for idx in range(account_count):
            path = f"{base_path}/{idx}"
            acct = Account.from_mnemonic(mnemonic, account_path=path)
            accounts.append(
                {
                    "index": idx,
                    "address": acct.address,
                    "private_key": acct.key.hex(),
                    "path": path,
                }
            )
        return {"rpc_url": cfg.get("rpc_url"), "accounts": accounts}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to derive accounts: {exc}") from exc


@app.post("/events", response_model=EventSpec)
def add_event(payload: EventIn) -> EventSpec:
    data = payload.model_dump()
    if data.get("filter_args") is None:
        data["filter_args"] = {}
    return storage.add_event(data)


@app.get("/events", response_model=List[EventSpec])
def list_events() -> List[EventSpec]:
    return storage.list_events()


@app.post("/events/{event_id}/start")
def start_event_listener(event_id: str) -> dict:
    try:
        event_manager.start_listener(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "started", "event_id": event_id}


@app.post("/events/{event_id}/stop")
def stop_event_listener(event_id: str) -> dict:
    event_manager.stop_listener(event_id)
    return {"status": "stopped", "event_id": event_id}


@app.get("/events/{event_id}/logs")
def list_event_logs(event_id: str) -> list:
    return [log.model_dump() for log in storage.list_event_logs(event_id)]


@app.post("/compute-watchers", response_model=ComputeWatcher)
def add_compute_watcher(payload: ComputeWatcherIn) -> ComputeWatcher:
    data = payload.model_dump()
    if data.get("compute_profiles") is None:
        data["compute_profiles"] = {}
    watcher = storage.add_compute_watcher(data)
    return watcher


@app.get("/compute-watchers", response_model=list[ComputeWatcher])
def list_compute_watchers() -> list[ComputeWatcher]:
    return storage.list_compute_watchers()


@app.post("/compute-watchers/{watcher_id}/start")
def start_compute_watcher(watcher_id: str) -> dict:
    try:
        compute_manager.start(watcher_id)
        storage.set_compute_watcher_enabled(watcher_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "started", "watcher_id": watcher_id}


@app.post("/compute-watchers/{watcher_id}/stop")
def stop_compute_watcher(watcher_id: str) -> dict:
    compute_manager.stop(watcher_id)
    storage.set_compute_watcher_enabled(watcher_id, False)
    return {"status": "stopped", "watcher_id": watcher_id}


@app.get("/compute-watchers/{watcher_id}/logs")
def list_compute_logs(watcher_id: str) -> list:
    return [log.model_dump() for log in storage.list_compute_logs(watcher_id)]


@app.on_event("startup")
def load_bootstrap_watchers() -> None:
    config_path = BASE_DIR / "config.yml"
    if not config_path.exists():
        return
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    for item in cfg.get("chain_identities", []) or []:
        name = item.get("name")
        if not name:
            continue
        existing = storage.get_identity_by_name(name)
        if existing:
            continue
        storage.add_identity(
            {
                "name": name,
                "chain_type": item.get("chain_type", "evm"),
                "rpc_url": item.get("rpc_url"),
                "private_key": item.get("private_key"),
                "address": item.get("address"),
                "notes": item.get("notes"),
                "metadata": item.get("metadata", {}),
            }
        )

    for item in cfg.get("compute_watchers", []) or []:
        name = item.get("name")
        if not name:
            continue
        existing = storage.get_compute_watcher_by_name(name)
        if existing:
            if item.get("enabled"):
                compute_manager.start(existing.id)
            continue
        identity_id = item.get("identity_id")
        if not identity_id and item.get("identity_name"):
            identity = storage.get_identity_by_name(item["identity_name"])
            if identity:
                identity_id = identity.id
        if not identity_id:
            continue

        watcher = storage.add_compute_watcher(
            {
                "name": name,
                "chain_type": item.get("chain_type", "evm"),
                "contract_address": item["contract_address"],
                "identity_id": identity_id,
                "poll_interval": item.get("poll_interval", 5),
                "compute_profiles": item.get("compute_profiles", {}),
                "enabled": item.get("enabled", False),
            }
        )
        if watcher.enabled:
            compute_manager.start(watcher.id)


# === Dashboard 静态资源 ===
frontend_dist = BASE_DIR.parent / "frontend" / "dist"
dashboard_dir = BASE_DIR.parent / "dashboard"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
elif dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")
