from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_account_repo,
    get_current_user,
    get_exchange_rate_repo,
    get_portfolio_repo,
    get_portfolio_snapshot_repo,
    get_profile_repo,
    get_tx_repo,
    get_user_repo,
    get_workspace_repo,
)
from app.domain.user import User
from app.api.schemas.profiles import (
    InviteMemberRequest,
    ProfileCreateRequest,
    ProfileNetWorthEntry,
    ProfileRenameRequest,
    ProfileResponse,
    UpdateMemberRoleRequest,
    WorkspaceCreateRequest,
    WorkspaceMemberResponse,
    WorkspaceNetWorthPoint,
    WorkspaceNetWorthResponse,
    WorkspaceNetWorthTimeseriesResponse,
    WorkspaceRenameRequest,
    WorkspaceResponse,
    _WORKSPACE_ROLE_TO_PROFILE_PERMISSION,
)
from app.engine.account_balance import compute_balance
from app.engine.account_timeseries import compute_timeseries, pick_granularity
from app.engine.portfolio_value import bucket_end_date


def _to_eur(amount: Decimal, currency: str, rates: dict[str, float]) -> Decimal:
    if currency == "EUR":
        return amount
    rate = rates.get(currency.upper())
    if not rate:
        return Decimal("0")
    return amount / Decimal(str(rate))


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


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def rename_workspace(
    workspace_id: str,
    payload: WorkspaceRenameRequest,
    user: User = Depends(get_current_user),
) -> WorkspaceResponse:
    _require_owner(user, workspace_id)
    repo = get_workspace_repo()
    try:
        w = repo.rename_workspace(workspace_id=workspace_id, name=payload.name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
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
    # Accorder l'accès au créateur en ADMIN
    profile_repo.grant_profile_access(user_id=user.id, profile_id=p.id, permission="ADMIN")
    # Accorder l'accès à tous les autres membres du workspace selon leur rôle
    for member in workspace_repo.list_members(workspace_id):
        if member.user_id == user.id:
            continue
        permission = _WORKSPACE_ROLE_TO_PROFILE_PERMISSION.get(member.role, "READ")
        profile_repo.grant_profile_access(user_id=member.user_id, profile_id=p.id, permission=permission)
    return ProfileResponse(**asdict(p))


@router.patch("/{workspace_id}/profiles/{profile_id}", response_model=ProfileResponse)
def rename_profile(
    workspace_id: str,
    profile_id: str,
    payload: ProfileRenameRequest,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")
    profile_repo = get_profile_repo()
    if not profile_repo.has_profile_access(user_id=user.id, profile_id=profile_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this profile")
    try:
        p = profile_repo.rename_profile(profile_id=profile_id, display_name=payload.display_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
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
# Profile cross-workspace linking
# ---------------------------------------------------------------------------

@router.post("/{workspace_id}/profiles/{profile_id}/link", status_code=201, response_model=ProfileResponse)
def link_profile(
    workspace_id: str,
    profile_id: str,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")

    profile_repo = get_profile_repo()
    permission = profile_repo.get_profile_permission(user_id=user.id, profile_id=profile_id)
    if permission != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only profile admin can link it to a workspace")

    if workspace_repo.has_profile_link(workspace_id=workspace_id, profile_id=profile_id):
        raise HTTPException(status_code=409, detail="Profile already linked to this workspace")

    workspace_repo.link_profile_to_workspace(workspace_id=workspace_id, profile_id=profile_id)

    # Accorder l'accès à tous les membres du workspace
    for member in workspace_repo.list_members(workspace_id):
        if member.user_id == user.id:
            continue
        member_permission = _WORKSPACE_ROLE_TO_PROFILE_PERMISSION.get(member.role, "READ")
        profile_repo.grant_profile_access(user_id=member.user_id, profile_id=profile_id, permission=member_permission)

    try:
        p = profile_repo.get_profile(profile_id=profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(**asdict(p))


@router.delete("/{workspace_id}/profiles/{profile_id}/link", status_code=204)
def unlink_profile(
    workspace_id: str,
    profile_id: str,
    user: User = Depends(get_current_user),
) -> None:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")

    profile_repo = get_profile_repo()
    permission = profile_repo.get_profile_permission(user_id=user.id, profile_id=profile_id)
    if permission != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only profile admin can unlink it")

    # Vérifier que ce n'est pas le home workspace (workspace_id == profiles.workspace_id)
    try:
        p = profile_repo.get_profile(profile_id=profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found")
    if p.workspace_id == workspace_id:
        raise HTTPException(
            status_code=422,
            detail="Cannot unlink a profile from its home workspace. Delete the profile instead.",
        )

    workspace_repo.unlink_profile_from_workspace(workspace_id=workspace_id, profile_id=profile_id)

    # Révoquer l'accès aux membres du workspace (sauf ADMIN — propriétaire du profil)
    for member in workspace_repo.list_members(workspace_id):
        mperm = profile_repo.get_profile_permission(user_id=member.user_id, profile_id=profile_id)
        if mperm and mperm != "ADMIN":
            profile_repo.revoke_profile_access(user_id=member.user_id, profile_id=profile_id)


# ---------------------------------------------------------------------------
# Workspace net worth
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/net-worth", response_model=WorkspaceNetWorthResponse)
def workspace_net_worth(
    workspace_id: str,
    at: dt.date | None = Query(default=None),
    user: User = Depends(get_current_user),
) -> WorkspaceNetWorthResponse:
    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")

    profile_repo = get_profile_repo()
    account_repo = get_account_repo()
    tx_repo = get_tx_repo()
    portfolio_repo = get_portfolio_repo()
    snapshot_repo = get_portfolio_snapshot_repo()
    rates = get_exchange_rate_repo().get_all()

    today = at or dt.date.today()
    profiles = profile_repo.list_profiles(workspace_id=workspace_id)
    accessible = [p for p in profiles if profile_repo.has_profile_access(user_id=user.id, profile_id=p.id)]

    profile_entries: list[ProfileNetWorthEntry] = []
    total_eur = Decimal("0")

    for p in accessible:
        accounts = account_repo.list_accounts(profile_id=p.id)
        txs: list = []
        for acc in accounts:
            txs.extend(tx_repo.list(account_id=acc.id, profile_id=p.id))
        portfolios = portfolio_repo.list(profile_id=p.id)
        snapshots = snapshot_repo.list(profile_id=p.id)

        accounts_eur = Decimal("0")
        for account in accounts:
            acc_txs = [t for t in txs if t.account_id == account.id]
            _, _, balance, _ = compute_balance(
                opening_balance=account.opening_balance,
                transactions=acc_txs,
                at=today,
            )
            accounts_eur += _to_eur(balance.amount, account.currency.value, rates)

        portfolios_eur = Decimal("0")
        for portfolio in portfolios:
            relevant = [s for s in snapshots if s.portfolio_id == portfolio.id and s.date <= today]
            if not relevant:
                continue
            latest = max(relevant, key=lambda s: (s.date, str(s.id)))
            portfolios_eur += _to_eur(latest.value.amount, portfolio.currency.value, rates)

        profile_total = accounts_eur + portfolios_eur
        total_eur += profile_total
        profile_entries.append(ProfileNetWorthEntry(
            profile_id=p.id,
            display_name=p.display_name,
            accounts_eur=str(accounts_eur.quantize(Decimal("0.01"))),
            portfolios_eur=str(portfolios_eur.quantize(Decimal("0.01"))),
            total_eur=str(profile_total.quantize(Decimal("0.01"))),
        ))

    return WorkspaceNetWorthResponse(
        workspace_id=workspace_id,
        currency="EUR",
        at=today,
        total_eur=str(total_eur.quantize(Decimal("0.01"))),
        profiles=profile_entries,
    )


@router.get("/{workspace_id}/net-worth/timeseries", response_model=WorkspaceNetWorthTimeseriesResponse)
def workspace_net_worth_timeseries(
    workspace_id: str,
    date_from: dt.date = Query(..., alias="from"),
    date_to: dt.date = Query(..., alias="to"),
    granularity: str = Query(default="auto", pattern="^(auto|daily|weekly|monthly|yearly)$"),
    user: User = Depends(get_current_user),
) -> WorkspaceNetWorthTimeseriesResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="from must be <= to")

    workspace_repo = get_workspace_repo()
    if not workspace_repo.has_workspace_membership(user_id=user.id, workspace_id=workspace_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this workspace")

    profile_repo = get_profile_repo()
    account_repo = get_account_repo()
    tx_repo = get_tx_repo()
    portfolio_repo = get_portfolio_repo()
    snapshot_repo = get_portfolio_snapshot_repo()
    rates = get_exchange_rate_repo().get_all()

    profiles = profile_repo.list_profiles(workspace_id=workspace_id)
    accessible = [p for p in profiles if profile_repo.has_profile_access(user_id=user.id, profile_id=p.id)]

    # Résoudre la granularité
    if granularity == "auto":
        granularity = pick_granularity(date_from, date_to)

    aggregated: dict[str, dict] = {}

    for p in accessible:
        accounts = account_repo.list_accounts(profile_id=p.id)
        txs: list = []
        for acc in accounts:
            txs.extend(tx_repo.list(account_id=acc.id, profile_id=p.id))
        portfolios = portfolio_repo.list(profile_id=p.id)
        snapshots = snapshot_repo.list(profile_id=p.id)

        # Générer les buckets via un compte quelconque (ou vide si aucun compte)
        if accounts:
            ref_txs = [t for t in txs if t.account_id == accounts[0].id]
            buckets_raw = compute_timeseries(
                opening_balance=accounts[0].opening_balance,
                transactions=ref_txs,
                date_from=date_from,
                date_to=date_to,
                granularity=granularity,
            )
            bucket_keys = [b["bucket"] for b in buckets_raw]
        else:
            bucket_keys = []

        for bucket in bucket_keys:
            as_of = bucket_end_date(bucket, granularity, date_from, date_to)

            nw_eur = Decimal("0")
            for account in accounts:
                acc_txs = [t for t in txs if t.account_id == account.id]
                _, _, balance, _ = compute_balance(
                    opening_balance=account.opening_balance,
                    transactions=acc_txs,
                    at=as_of,
                )
                nw_eur += _to_eur(balance.amount, account.currency.value, rates)

            for portfolio in portfolios:
                relevant = [s for s in snapshots if s.portfolio_id == portfolio.id and s.date <= as_of]
                if not relevant:
                    continue
                latest = max(relevant, key=lambda s: (s.date, str(s.id)))
                nw_eur += _to_eur(latest.value.amount, portfolio.currency.value, rates)

            if bucket not in aggregated:
                aggregated[bucket] = {"total": Decimal("0"), "by_profile": {}}
            aggregated[bucket]["total"] += nw_eur
            aggregated[bucket]["by_profile"][p.id] = str(nw_eur.quantize(Decimal("0.01")))

    points = [
        WorkspaceNetWorthPoint(
            bucket=bucket,
            total_eur=str(aggregated[bucket]["total"].quantize(Decimal("0.01"))),
            by_profile=aggregated[bucket]["by_profile"],
        )
        for bucket in sorted(aggregated.keys())
    ]

    return WorkspaceNetWorthTimeseriesResponse(
        workspace_id=workspace_id,
        currency="EUR",
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
        points=points,
    )


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
