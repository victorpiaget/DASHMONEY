from pydantic import BaseModel


class SubcategoryResponse(BaseModel):
    id: str
    name: str


class CategoryResponse(BaseModel):
    id: str
    name: str
    subcategories: list[SubcategoryResponse]


class CategoryCreateRequest(BaseModel):
    name: str


class SubcategoryCreateRequest(BaseModel):
    name: str
