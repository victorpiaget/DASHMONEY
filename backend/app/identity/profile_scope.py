from __future__ import annotations


def resolve_profile_id(profile_id: str | None) -> str:
    """
    Valide et normalise un profile_id.
    Lève ValueError si None ou vide — plus de fallback silencieux sur DEFAULT_PROFILE_ID.
    Le profile_id doit toujours être fourni explicitement via RequestContext.
    """
    if profile_id is None:
        raise ValueError("profile_id is required and cannot be None")
    pid = profile_id.strip()
    if not pid:
        raise ValueError("profile_id cannot be blank")
    return pid
