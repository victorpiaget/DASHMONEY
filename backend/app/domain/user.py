from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    is_disabled: bool
    created_at: dt.datetime
