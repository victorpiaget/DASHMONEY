from __future__ import annotations

from pydantic import BaseModel


class BudgetEnvelopeRequest(BaseModel):
    category: str
    subcategory: str | None = None
    kind: str
    amount: str


class BudgetEnvelopeResponse(BaseModel):
    id: str
    category: str
    subcategory: str | None
    kind: str
    amount: str
    currency: str
    profile_id: str


class BudgetComparisonResponse(BaseModel):
    category: str
    subcategory: str | None
    kind: str
    planned: str
    actual: str
    delta: str
    percent: str


class BudgetSynthesisResponse(BaseModel):
    total_income_planned: str
    total_income_actual: str
    total_expense_planned: str
    total_expense_actual: str
    net_planned: str
    net_actual: str


class BudgetComparisonFullResponse(BaseModel):
    month: str
    currency: str
    synthesis: BudgetSynthesisResponse
    comparisons: list[BudgetComparisonResponse]
    profile_id: str


class BudgetHistoryMonthResponse(BaseModel):
    month: str  # "YYYY-MM"
    income_actual: str
    expense_actual: str
    net_actual: str
    income_planned: str
    expense_planned: str


class BudgetHistoryResponse(BaseModel):
    months: list[BudgetHistoryMonthResponse]
    currency: str
    profile_id: str


class BudgetCategoryItem(BaseModel):
    category: str
    subcategories: list[str]


class BudgetCategoriesResponse(BaseModel):
    income: list[BudgetCategoryItem]
    expense: list[BudgetCategoryItem]
