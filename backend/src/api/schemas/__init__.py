"""Request bodies. Responses are plain dicts from the controllers."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Toggle(BaseModel):
    on: bool


class Paused(BaseModel):
    paused: bool


class RiskUpdate(BaseModel):
    fields: dict[str, Any]


class NewEvent(BaseModel):
    ts: float
    title: str = Field(min_length=1, max_length=200)
    impact: str
    kind: str = "other"
    coins: list[str] = []


class Network(BaseModel):
    network: str


class AccountAddress(BaseModel):
    address: str


class AgentKey(BaseModel):
    network: str
    key: str


class AdminConsole(BaseModel):
    enabled: bool
    nickname: Optional[str] = ""
