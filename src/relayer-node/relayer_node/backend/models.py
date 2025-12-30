from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid4())


class ChainIdentity(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    chain_type: str
    rpc_url: Optional[str] = None
    private_key: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelayRoute(BaseModel):
    id: str = Field(default_factory=new_id)
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
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_block: Optional[int] = None


class RelayLog(BaseModel):
    id: str = Field(default_factory=new_id)
    route_id: str
    message_id: str
    direction: str
    status: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    created_at: float
