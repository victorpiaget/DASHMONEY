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