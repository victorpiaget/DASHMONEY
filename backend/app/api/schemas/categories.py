from typing import Literal, Optional

from pydantic import BaseModel


CategoryNatureLiteral = Literal["NEED", "WANT", "SAVING"]


class SubcategoryResponse(BaseModel):
    id: str
    name: str


class CategoryResponse(BaseModel):
    id: str
    name: str
    nature: Optional[CategoryNatureLiteral] = None
    subcategories: list[SubcategoryResponse]


class CategoryCreateRequest(BaseModel):
    name: str
    nature: Optional[CategoryNatureLiteral] = None


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    nature: Optional[CategoryNatureLiteral] = None
    clear_nature: bool = False


class SubcategoryCreateRequest(BaseModel):
    name: str
