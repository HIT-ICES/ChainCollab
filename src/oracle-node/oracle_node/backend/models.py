from __future__ import annotations

import secrets
import string
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


def _random_id(prefix: str) -> str:
    token = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return f"{prefix}_{token}"


class DataSource(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("ds"))
    name: str
    type: str
    endpoint: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContractInterface(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("iface"))
    name: str
    chain_type: str = Field(description="evm|fabric 等")
    address: Optional[str] = None
    abi: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None


class EventSpec(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("evt"))
    name: str
    chain_type: str = Field(description="evm 或 fabric")
    contract_interface_id: str
    event_name: str
    filter_args: Dict[str, Any] = Field(default_factory=dict)
    rpc_url: Optional[str] = None
    start_block: Optional[int] = None
    poll_interval: int = Field(5, description="轮询秒数")
    confirmations: int = Field(0, description="需要的区块确认数")
    callback_url: Optional[str] = Field(
        default=None, description="可选 HTTP 回调地址，事件触发时会 POST 数据"
    )

    @validator("chain_type")
    def validate_chain(cls, v: str) -> str:
        allowed = {"evm", "fabric"}
        if v not in allowed:
            raise ValueError(f"chain_type must be in {allowed}")
        return v


class EventLog(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("log"))
    event_id: str
    payload: Dict[str, Any]


class ChainIdentity(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("idn"))
    name: str
    chain_type: str = Field(description="evm|fabric")
    rpc_url: Optional[str] = None
    private_key: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("chain_type")
    def validate_chain(cls, v: str) -> str:
        allowed = {"evm", "fabric"}
        if v not in allowed:
            raise ValueError(f"chain_type must be in {allowed}")
        return v


class ComputeWatcher(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("watch"))
    name: str
    chain_type: str = Field(description="evm")
    contract_address: str
    identity_id: str
    poll_interval: int = Field(5, description="轮询秒数")
    compute_profiles: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    enabled: bool = False

    @validator("chain_type")
    def validate_chain(cls, v: str) -> str:
        allowed = {"evm"}
        if v not in allowed:
            raise ValueError(f"chain_type must be in {allowed}")
        return v


class ComputeTaskLog(BaseModel):
    id: str = Field(default_factory=lambda: _random_id("clog"))
    watcher_id: str
    task_id: int
    compute_type: str
    payload_hash: str
    result: str
    tx_hash: Optional[str] = None
    status: str = "submitted"
    error: Optional[str] = None
