from __future__ import annotations
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_profile_repo, get_workspace_repo
from app.domain.user import User
from app.api.schemas.profiles import (
    ProfileCreateRequest,
    ProfileResponse,
    WorkspaceCreateRequest,
    WorkspaceResponse,
)


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces() -> list[WorkspaceResponse]:
    repo = get_workspace_repo()
    return [WorkspaceResponse(**asdict(w)) for w in repo.list_workspaces()]


@router.post("", status_code=201, response_model=WorkspaceResponse)
def create_workspace(payload: WorkspaceCreateRequest) -> WorkspaceResponse:
    repo = get_workspace_repo()
    try:
        w = repo.create_workspace(name=payload.name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return WorkspaceResponse(**asdict(w))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: str) -> WorkspaceResponse:
    repo = get_workspace_repo()
    try:
        w = repo.get_workspace(workspace_id=workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse(**asdict(w))


@router.get("/{workspace_id}/profiles", response_model=list[ProfileResponse])
def list_profiles(workspace_id: str) -> list[ProfileResponse]:
    repo = get_profile_repo()
    try:
        profiles = repo.list_profiles(workspace_id=workspace_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return [ProfileResponse(**asdict(p)) for p in profiles]


@router.post("/{workspace_id}/profiles", status_code=201, response_model=ProfileResponse)
def create_profile(
    workspace_id: str,
    payload: ProfileCreateRequest,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    repo = get_profile_repo()
    try:
        p = repo.create_profile(workspace_id=workspace_id, display_name=payload.display_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))
    repo.grant_profile_access(user_id=user.id, profile_id=p.id, permission="OWNER")
    return ProfileResponse(**asdict(p))


profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])


@profiles_router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: str) -> ProfileResponse:
    repo = get_profile_repo()
    try:
        p = repo.get_profile(profile_id=profile_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(**asdict(p))


@profiles_router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str) -> None:
    repo = get_profile_repo()
    ok = repo.delete_profile(profile_id=profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")