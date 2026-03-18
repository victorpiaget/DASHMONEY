from __future__ import annotations

import datetime as dt
from decimal import Decimal
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


class WorkspaceRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ProfileRenameRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(pattern="^(OWNER|MEMBER|READ_ONLY)$")


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    email: str
    role: str


class ProfileNetWorthEntry(BaseModel):
    profile_id: str
    display_name: str
    accounts_eur: str
    portfolios_eur: str
    total_eur: str


class WorkspaceNetWorthResponse(BaseModel):
    workspace_id: str
    currency: str = "EUR"
    at: dt.date | None
    total_eur: str
    profiles: list[ProfileNetWorthEntry]


class WorkspaceNetWorthPoint(BaseModel):
    bucket: str
    total_eur: str
    by_profile: dict[str, str]


class WorkspaceNetWorthTimeseriesResponse(BaseModel):
    workspace_id: str
    currency: str = "EUR"
    date_from: dt.date
    date_to: dt.date
    granularity: str
    points: list[WorkspaceNetWorthPoint]