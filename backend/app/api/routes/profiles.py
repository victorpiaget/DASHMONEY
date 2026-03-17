from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status

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
def list_workspaces(user: User = Depends(get_current_user)) -> list[WorkspaceResponse]:
    repo = get_workspace_repo()
    return [WorkspaceResponse(**asdict(w)) for w in repo.list_workspaces_for_user(user.id)]


@router.post("", status_code=201, response_model=WorkspaceResponse)
def create_workspace(
    payload: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    repo = get_workspace_repo()
    try:
        w = repo.create_workspace(name=payload.name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    repo.add_workspace_membership(user_id=user.id, workspace_id=w.id, role="OWNER")
    return WorkspaceResponse(**asdict(w))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    repo = get_workspace_repo()
    if not repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")
    try:
        w = repo.get_workspace(workspace_id=workspace_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse(**asdict(w))


@router.get("/{workspace_id}/profiles", response_model=list[ProfileResponse])
def list_profiles(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> list[ProfileResponse]:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")
    profile_repo = get_profile_repo()
    profiles = profile_repo.list_profiles(workspace_id=workspace_id)
    accessible = [p for p in profiles if profile_repo.has_profile_access(user_id=user.id, profile_id=p.id)]
    return [ProfileResponse(**asdict(p)) for p in accessible]


@router.post("/{workspace_id}/profiles", status_code=201, response_model=ProfileResponse)
def create_profile(
    workspace_id: str,
    payload: ProfileCreateRequest,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")
    profile_repo = get_profile_repo()
    try:
        p = profile_repo.create_profile(workspace_id=workspace_id, display_name=payload.display_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))
    profile_repo.grant_profile_access(user_id=user.id, profile_id=p.id, permission="OWNER")
    return ProfileResponse(**asdict(p))


profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])


@profiles_router.get("", response_model=list[ProfileResponse])
def list_my_profiles(user: User = Depends(get_current_user)) -> list[ProfileResponse]:
    repo = get_profile_repo()
    profiles = repo.list_profiles_for_user(user.id)
    return [ProfileResponse(**asdict(p)) for p in profiles]


@profiles_router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(
    profile_id: str,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    repo = get_profile_repo()
    if not repo.has_profile_access(user_id=user.id, profile_id=profile_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this profile")
    try:
        p = repo.get_profile(profile_id=profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(**asdict(p))


@profiles_router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: str,
    user: User = Depends(get_current_user),
) -> None:
    repo = get_profile_repo()
    if not repo.has_profile_access(user_id=user.id, profile_id=profile_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this profile")
    ok = repo.delete_profile(profile_id=profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
