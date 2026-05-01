from datetime import datetime
from pydantic import BaseModel, EmailStr


class SupplierBase(BaseModel):
    supplier_name: str
    country: str
    risk_level: str
    approved_status: bool
    missing_documents: str | None = None
    contact_email: str | None = None
    category: str | None = None


class SupplierCreate(SupplierBase):
    supplier_id: str


class SupplierOut(SupplierBase):
    supplier_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierDetail(SupplierOut):
    total_po_amount: float = 0.0
    po_count: int = 0
    open_po_count: int = 0
