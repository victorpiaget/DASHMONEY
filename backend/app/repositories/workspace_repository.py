from __future__ import annotations

from typing import Protocol

from app.domain.workspace import Workspace


class WorkspaceRepository(Protocol):
    def list_workspaces(self) -> list[Workspace]: ...
    def get_workspace(self, *, workspace_id: str) -> Workspace: ...
    def create_workspace(self, *, name: str) -> Workspace: ...