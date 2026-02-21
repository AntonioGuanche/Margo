"""Billing Pydantic schemas."""

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan: str  # "pro" or "multi"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PlanInfoResponse(BaseModel):
    current_plan: str
    max_recipes: int | None
    max_invoices_per_month: int | None
    current_recipes: int
    current_invoices_this_month: int
    stripe_customer_id: str | None
    can_manage_billing: bool


class PortalResponse(BaseModel):
    portal_url: str
