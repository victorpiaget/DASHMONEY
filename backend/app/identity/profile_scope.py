from __future__ import annotations

from app.identity.defaults import DEFAULT_PROFILE_ID


def resolve_profile_id(profile_id: str | None) -> str:
    """
    Normalize profile scope:
    - None / blank -> DEFAULT_PROFILE_ID
    - otherwise -> stripped value
    """
    if profile_id is None:
        return DEFAULT_PROFILE_ID
    pid = profile_id.strip()
    return pid or DEFAULT_PROFILE_ID
