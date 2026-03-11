from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Workspace:
    id: str
    name: str
    created_at: dt.datetime