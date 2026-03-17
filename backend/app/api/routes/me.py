from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_profile_repo, get_workspace_repo
from app.api.schemas.profiles import MeResponse, ProfileResponse, WorkspaceWithProfilesResponse
from app.domain.user import User

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user)) -> MeResponse:
    workspace_repo = get_workspace_repo()
    profile_repo = get_profile_repo()

    workspaces = workspace_repo.list_workspaces_for_user(user.id)
    workspace_responses = []
    for w in workspaces:
        profiles = profile_repo.list_profiles(workspace_id=w.id)
        accessible = [
            ProfileResponse(**asdict(p))
            for p in profiles
            if profile_repo.has_profile_access(user_id=user.id, profile_id=p.id)
        ]
        workspace_responses.append(
            WorkspaceWithProfilesResponse(
                id=w.id,
                name=w.name,
                created_at=w.created_at,
                profiles=accessible,
            )
        )

    return MeResponse(id=user.id, email=user.email, workspaces=workspace_responses)
