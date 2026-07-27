from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


CategoryNatureLiteral = Literal["NEED", "WANT", "SAVING"]


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
    savings_actual: str  # valeur absolue, toujours positive
    savings_rate: str    # "0.0000".."1.0000" (frontend × 100 pour affichage %)


class BudgetBucketsResponse(BaseModel):
    needs: str
    wants: str
    savings: str
    uncategorized: str
    total_expenses: str  # NEEDS + WANTS + UNCAT (exclut SAVING)


class BudgetComparisonFullResponse(BaseModel):
    month: str
    currency: str
    synthesis: BudgetSynthesisResponse
    comparisons: list[BudgetComparisonResponse]
    buckets: BudgetBucketsResponse
    profile_id: str


class BudgetHistoryMonthResponse(BaseModel):
    month: str  # "YYYY-MM"
    income_actual: str
    expense_actual: str
    net_actual: str
    income_planned: str
    expense_planned: str
    savings_actual: str
    savings_rate: str


class BudgetHistoryResponse(BaseModel):
    months: list[BudgetHistoryMonthResponse]
    currency: str
    profile_id: str


class BudgetFlowIncomeSourceResponse(BaseModel):
    category: str
    subcategory: str | None
    amount: str


class BudgetFlowSubcategoryResponse(BaseModel):
    subcategory: str | None
    amount: str


class BudgetFlowExpenseCategoryResponse(BaseModel):
    category: str
    nature: Optional[CategoryNatureLiteral]
    amount: str
    subcategories: list[BudgetFlowSubcategoryResponse]


class BudgetFlowSummaryResponse(BaseModel):
    total_income: str
    total_expenses: str
    total_savings: str
    total_outflows: str
    balance: str
    remaining: str
    deficit: str


class BudgetFlowResponse(BaseModel):
    date_from: str
    date_to: str
    currency: str
    income_sources: list[BudgetFlowIncomeSourceResponse]
    expense_categories: list[BudgetFlowExpenseCategoryResponse]
    summary: BudgetFlowSummaryResponse
    profile_id: str


class BudgetCategoryItem(BaseModel):
    category: str
    subcategories: list[str]
    nature: Optional[CategoryNatureLiteral] = None


class BudgetCategoriesResponse(BaseModel):
    income: list[BudgetCategoryItem]
    expense: list[BudgetCategoryItem]


class BudgetAutoBudgetSuggestion(BaseModel):
    category: str
    subcategory: Optional[str]
    kind: str
    nature: Optional[CategoryNatureLiteral]
    median_amount: str
    occurrences: int


class BudgetAutoBudgetResponse(BaseModel):
    based_on_months: int
    from_month: str  # "YYYY-MM"
    to_month: str    # "YYYY-MM"
    suggestions: list[BudgetAutoBudgetSuggestion]
    currency: str
    profile_id: str
