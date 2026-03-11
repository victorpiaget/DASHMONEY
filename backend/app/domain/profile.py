from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    workspace_id: str
    display_name: str
    created_at: dt.datetime