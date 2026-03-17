from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_profile_repo, get_user_repo, get_workspace_repo
from app.domain.user import User
from app.api.schemas.profiles import (
    InviteMemberRequest,
    ProfileCreateRequest,
    ProfileResponse,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    _WORKSPACE_ROLE_TO_PROFILE_PERMISSION,
)


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _require_owner(user: User, workspace_id: str) -> None:
    repo = get_workspace_repo()
    role = repo.get_membership_role(user_id=user.id, workspace_id=workspace_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")
    if role != "OWNER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace owners can perform this action")


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
    profile_repo.grant_profile_access(user_id=user.id, profile_id=p.id, permission="ADMIN")
    return ProfileResponse(**asdict(p))


# ---------------------------------------------------------------------------
# Members management
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
def list_members(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> list[WorkspaceMemberResponse]:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")
    members = workspace_repo.list_members(workspace_id)
    return [WorkspaceMemberResponse(user_id=m.user_id, email=m.email, role=m.role) for m in members]


@router.post("/{workspace_id}/members/invite", status_code=201, response_model=WorkspaceMemberResponse)
def invite_member(
    workspace_id: str,
    payload: InviteMemberRequest,
    user: User = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    _require_owner(user, workspace_id)

    user_repo = get_user_repo()
    target = user_repo.get_by_email(payload.email.strip().lower())
    if target is None:
        raise HTTPException(status_code=404, detail=f"No user found with email '{payload.email}'")

    workspace_repo = get_workspace_repo()
    if workspace_repo.has_workspace_membership(user_id=target.id, workspace_id=workspace_id):
        raise HTTPException(status_code=409, detail="User is already a member of this workspace")

    granted_role = payload.role
    granted_permission = _WORKSPACE_ROLE_TO_PROFILE_PERMISSION[granted_role]
    workspace_repo.add_workspace_membership(user_id=target.id, workspace_id=workspace_id, role=granted_role)

    profile_repo = get_profile_repo()
    for p in profile_repo.list_profiles(workspace_id=workspace_id):
        profile_repo.grant_profile_access(user_id=target.id, profile_id=p.id, permission=granted_permission)

    return WorkspaceMemberResponse(user_id=target.id, email=target.email, role=granted_role)


@router.delete("/{workspace_id}/members/{target_user_id}", status_code=204)
def remove_member(
    workspace_id: str,
    target_user_id: str,
    user: User = Depends(get_current_user),
) -> None:
    _require_owner(user, workspace_id)

    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=target_user_id, workspace_id=workspace_id):
        raise HTTPException(status_code=404, detail="Member not found in this workspace")

    # Ne pas supprimer le dernier OWNER
    target_role = workspace_repo.get_membership_role(user_id=target_user_id, workspace_id=workspace_id)
    if target_role == "OWNER" and workspace_repo.count_owners(workspace_id) <= 1:
        raise HTTPException(
            status_code=422,
            detail="Cannot remove the last owner of a workspace",
        )

    workspace_repo.remove_member(user_id=target_user_id, workspace_id=workspace_id)
    get_profile_repo().revoke_workspace_access(user_id=target_user_id, workspace_id=workspace_id)


@router.patch("/{workspace_id}/members/{target_user_id}", response_model=WorkspaceMemberResponse)
def update_member_role(
    workspace_id: str,
    target_user_id: str,
    payload: UpdateMemberRoleRequest,
    user: User = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    _require_owner(user, workspace_id)

    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=target_user_id, workspace_id=workspace_id):
        raise HTTPException(status_code=404, detail="Member not found in this workspace")

    # On ne peut pas rétrograder le dernier OWNER
    current_role = workspace_repo.get_membership_role(user_id=target_user_id, workspace_id=workspace_id)
    if current_role == "OWNER" and payload.role != "OWNER" and workspace_repo.count_owners(workspace_id) <= 1:
        raise HTTPException(
            status_code=422,
            detail="Cannot downgrade the last owner of a workspace",
        )

    new_permission = _WORKSPACE_ROLE_TO_PROFILE_PERMISSION[payload.role]
    workspace_repo.update_membership_role(user_id=target_user_id, workspace_id=workspace_id, new_role=payload.role)
    get_profile_repo().update_workspace_permissions(
        user_id=target_user_id, workspace_id=workspace_id, permission=new_permission
    )

    user_repo = get_user_repo()
    try:
        target = user_repo.get(target_user_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")

    return WorkspaceMemberResponse(user_id=target_user_id, email=target.email, role=payload.role)


# ---------------------------------------------------------------------------
# /profiles router
# ---------------------------------------------------------------------------

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
