from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Supplier, PurchaseOrder
from app.schemas.suppliers import SupplierOut, SupplierDetail


class SupplierService:
    def __init__(self, db: Session):
        self.db = db

    def list_suppliers(
        self,
        skip: int = 0,
        limit: int = 50,
        risk_level: str | None = None,
        approved: bool | None = None,
    ) -> list[SupplierOut]:
        q = self.db.query(Supplier)
        if risk_level:
            q = q.filter(Supplier.risk_level == risk_level.upper())
        if approved is not None:
            q = q.filter(Supplier.approved_status == approved)
        return q.offset(skip).limit(limit).all()

    def get_supplier_detail(self, supplier_id: str) -> SupplierDetail | None:
        supplier = (
            self.db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
        )
        if not supplier:
            return None

        agg = (
            self.db.query(
                func.coalesce(func.sum(PurchaseOrder.amount), 0).label("total"),
                func.count(PurchaseOrder.id).label("count"),
            )
            .filter(PurchaseOrder.supplier_id == supplier_id)
            .first()
        )

        open_count = (
            self.db.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.supplier_id == supplier_id, PurchaseOrder.status == "OPEN")
            .scalar()
        )

        detail = SupplierDetail.model_validate(supplier)
        detail.total_po_amount = float(agg.total or 0)
        detail.po_count = agg.count or 0
        detail.open_po_count = open_count or 0
        return detail

    def get_supplier_profile_dict(self, supplier_id: str) -> dict | None:
        """Used by agent tools — returns a plain dict for LLM consumption."""
        detail = self.get_supplier_detail(supplier_id)
        if not detail:
            return None
        return detail.model_dump()
