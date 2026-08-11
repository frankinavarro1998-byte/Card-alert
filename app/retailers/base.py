from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Status = Literal["IN_STOCK", "OUT_OF_STOCK", "UNKNOWN"]


@dataclass
class CheckResult:
    status: Status
    price: float | None = None
    reason: str | None = None


class RetailerChecker:
    name = "generic"

    async def check(self, url: str) -> CheckResult:
        raise NotImplementedError
