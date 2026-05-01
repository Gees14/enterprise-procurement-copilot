from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class PurchaseOrderBase(BaseModel):
    item_description: str
    category: str | None = None
    unspsc_code: str | None = None
    amount: Decimal
    currency: str = "USD"
    status: str


class PurchaseOrderCreate(PurchaseOrderBase):
    po_id: str
    supplier_id: str
    po_date: datetime


class PurchaseOrderOut(PurchaseOrderCreate):
    created_at: datetime
    model_config = {"from_attributes": True}


class POAnalytics(BaseModel):
    total_spend: float
    total_orders: int
    open_orders: int
    closed_orders: int
    cancelled_orders: int
    top_suppliers: list[dict]
    spend_by_category: list[dict]
    monthly_spend: list[dict]
