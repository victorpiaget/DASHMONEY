from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_category_repo, get_request_context
from app.api.schemas.categories import (
    CategoryCreateRequest,
    CategoryResponse,
    SubcategoryCreateRequest,
    SubcategoryResponse,
)
from app.identity.request_context import RequestContext

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(ctx: RequestContext = Depends(get_request_context)) -> list[CategoryResponse]:
    repo = get_category_repo()
    rows = repo.list(profile_id=ctx.profile_id)
    return [
        CategoryResponse(
            id=r["id"],
            name=r["name"],
            subcategories=[SubcategoryResponse(id=s["id"], name=s["name"]) for s in r["subcategories"]],
        )
        for r in rows
    ]


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    req: CategoryCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> CategoryResponse:
    repo = get_category_repo()
    try:
        row = repo.add_category(req.name, profile_id=ctx.profile_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return CategoryResponse(id=row["id"], name=row["name"], subcategories=[])


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    ctx: RequestContext = Depends(get_request_context),
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
    ctx: RequestContext = Depends(get_request_context),
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
    ctx: RequestContext = Depends(get_request_context),
) -> Response:
    repo = get_category_repo()
    deleted = repo.delete_subcategory(subcategory_id, profile_id=ctx.profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    return Response(status_code=204)
