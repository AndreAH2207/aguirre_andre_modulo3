from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ReleaseRequest(BaseModel):
    """Sale release request extracted from natural language.

    Fields are optional: if the user does not give them, the LLM must return
    null instead of inventing them, and the workflow stops as "blocked".
    """

    customer_id: str | None = None
    sku: str | None = None
    quantity: int | None = Field(default=None, gt=0)


class FinanceDecision(BaseModel):
    """Finance / credit answer when resuming a paused release.

    An explicit value instead of a boolean: a text like "no" would be truthy and
    could release an order by mistake.
    """

    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1)
    comment: str | None = None


class ReleaseState(TypedDict, total=False):
    """Small, explicit state of the sale release workflow (no full master records)."""

    request_text: str

    customer_id: str
    sku: str
    quantity: int
    order_amount_usd: float

    credit_status: str
    credit_limit_usd: float
    current_exposure_usd: float
    available_credit_usd: float
    projected_exposure_usd: float

    decision: str
    reasons: list[str]

    finance_decision: str
    reviewer: str
    finance_comment: str | None

    status: str
    message: str
