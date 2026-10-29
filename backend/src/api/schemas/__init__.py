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


class StrategyIn(BaseModel):
    name: str = Field(max_length=200)
    params: dict[str, Any] = Field(default_factory=dict)
    notes: str = Field("", max_length=2000)


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


class BacktestRequest(BaseModel):
    strategy: str
    coin: str = Field(min_length=1, max_length=20)
    bars: int = 1500


class Telegram(BaseModel):
    enabled: bool
    chat_id: str = ""
    token: str = ""


class TuneRequest(BaseModel):
    strategy: str
    coin: str = Field(min_length=1, max_length=20)
    bars: int = 3000
    folds: int = Field(default=4, ge=1, le=8)


class JournalIn(BaseModel):
    note: str = Field("", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    mood: Optional[int] = Field(None, ge=1, le=5)
