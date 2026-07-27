from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_category_repo, get_request_context, get_write_context
from app.api.schemas.categories import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    SubcategoryCreateRequest,
    SubcategoryResponse,
)
from app.domain.category import CategoryNature
from app.identity.request_context import RequestContext

router = APIRouter(prefix="/categories", tags=["categories"])


def _row_to_response(row: dict) -> CategoryResponse:
    return CategoryResponse(
        id=row["id"],
        name=row["name"],
        nature=row.get("nature"),
        subcategories=[SubcategoryResponse(id=s["id"], name=s["name"]) for s in row["subcategories"]],
    )


@router.get("", response_model=list[CategoryResponse])
def list_categories(ctx: RequestContext = Depends(get_request_context)) -> list[CategoryResponse]:
    repo = get_category_repo()
    rows = repo.list(profile_id=ctx.profile_id)
    return [_row_to_response(r) for r in rows]


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    req: CategoryCreateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> CategoryResponse:
    repo = get_category_repo()
    try:
        row = repo.add_category(req.name, profile_id=ctx.profile_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if req.nature is not None:
        row = repo.update_category(
            row["id"],
            nature=CategoryNature(req.nature),
            profile_id=ctx.profile_id,
        )

    return _row_to_response(row)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    req: CategoryUpdateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> CategoryResponse:
    repo = get_category_repo()
    nature = CategoryNature(req.nature) if req.nature is not None else None
    try:
        row = repo.update_category(
            category_id,
            name=req.name,
            nature=nature,
            clear_nature=req.clear_nature,
            profile_id=ctx.profile_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _row_to_response(row)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    ctx: RequestContext = Depends(get_write_context),
) -> Response:
    repo = get_category_repo()
    deleted = repo.delete_category(category_id, profile_id=ctx.profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return Response(status_code=204)


@router.post("/{category_id}/subcategories", response_model=SubcategoryResponse, status_code=201)
def add_subcategory(
    category_id: str,
    req: SubcategoryCreateRequest,
    ctx: RequestContext = Depends(get_write_context),
) -> SubcategoryResponse:
    repo = get_category_repo()
    try:
        row = repo.add_subcategory(category_id, req.name, profile_id=ctx.profile_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return SubcategoryResponse(id=row["id"], name=row["name"])


@router.delete("/{category_id}/subcategories/{subcategory_id}", status_code=204)
def delete_subcategory(
    category_id: str,
    subcategory_id: str,
    ctx: RequestContext = Depends(get_write_context),
) -> Response:
    repo = get_category_repo()
    deleted = repo.delete_subcategory(subcategory_id, profile_id=ctx.profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    return Response(status_code=204)
