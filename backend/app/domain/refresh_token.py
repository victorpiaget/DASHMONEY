from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RefreshToken:
    id: str
    user_id: str
    token_hash: str
    expires_at: dt.datetime
    revoked: bool
    created_at: dt.datetime
