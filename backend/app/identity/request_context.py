from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    user_id: str
    profile_id: str   # already resolved (never None)
    permission: str   # ADMIN | WRITE | READ
