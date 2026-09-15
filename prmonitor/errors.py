"""Typed, JSON-safe engine errors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import PrMonitorError


@dataclass
class EngineError(PrMonitorError):
    code: str
    message: str
    retryable: bool = False
    stage: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message,
                "retryable": self.retryable, "stage": self.stage,
                "details": self.details}


class ConflictError(EngineError):
    pass


class IntegrityError(EngineError):
    pass
