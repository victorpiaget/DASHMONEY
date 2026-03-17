from __future__ import annotations

import datetime as dt
from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    created_at: dt.datetime


class ProfileCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)


class ProfileResponse(BaseModel):
    id: str
    workspace_id: str
    display_name: str
    created_at: dt.datetime


class WorkspaceWithProfilesResponse(BaseModel):
    id: str
    name: str
    created_at: dt.datetime
    profiles: list[ProfileResponse]


class MeResponse(BaseModel):
    id: str
    email: str
    workspaces: list[WorkspaceWithProfilesResponse]


_VALID_WORKSPACE_ROLES = {"OWNER", "MEMBER", "READ_ONLY"}
_WORKSPACE_ROLE_TO_PROFILE_PERMISSION = {"OWNER": "ADMIN", "MEMBER": "WRITE", "READ_ONLY": "READ"}


class InviteMemberRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    role: str = Field(default="MEMBER", pattern="^(OWNER|MEMBER|READ_ONLY)$")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(pattern="^(OWNER|MEMBER|READ_ONLY)$")


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    email: str
    role: str