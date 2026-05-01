from collections import defaultdict
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.db.models import PurchaseOrder, Supplier
from app.schemas.purchase_orders import PurchaseOrderOut, POAnalytics


class PurchaseOrderService:
    def __init__(self, db: Session):
        self.db = db

    def list_purchase_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        supplier_id: str | None = None,
        status: str | None = None,
    ) -> list[PurchaseOrderOut]:
        q = self.db.query(PurchaseOrder)
        if supplier_id:
            q = q.filter(PurchaseOrder.supplier_id == supplier_id)
        if status:
            q = q.filter(PurchaseOrder.status == status.upper())
        return q.order_by(desc(PurchaseOrder.po_date)).offset(skip).limit(limit).all()

    def get_analytics(self) -> POAnalytics:
        all_pos = self.db.query(PurchaseOrder).all()

        total_spend = sum(float(po.amount) for po in all_pos)
        status_counts = defaultdict(int)
        category_spend: dict[str, float] = defaultdict(float)
        monthly_spend: dict[str, float] = defaultdict(float)

        for po in all_pos:
            status_counts[po.status] += 1
            cat = po.category or "Uncategorized"
            category_spend[cat] += float(po.amount)
            month_key = po.po_date.strftime("%Y-%m")
            monthly_spend[month_key] += float(po.amount)

        # Top suppliers by total spend
        top_rows = (
            self.db.query(
                PurchaseOrder.supplier_id,
                Supplier.supplier_name,
                func.sum(PurchaseOrder.amount).label("total"),
                func.count(PurchaseOrder.id).label("count"),
            )
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.supplier_id)
            .group_by(PurchaseOrder.supplier_id, Supplier.supplier_name)
            .order_by(desc("total"))
            .limit(10)
            .all()
        )

        return POAnalytics(
            total_spend=total_spend,
            total_orders=len(all_pos),
            open_orders=status_counts["OPEN"],
            closed_orders=status_counts["CLOSED"],
            cancelled_orders=status_counts["CANCELLED"],
            top_suppliers=[
                {
                    "supplier_id": r.supplier_id,
                    "supplier_name": r.supplier_name,
                    "total_spend": float(r.total),
                    "po_count": r.count,
                }
                for r in top_rows
            ],
            spend_by_category=[
                {"category": k, "total_spend": v}
                for k, v in sorted(category_spend.items(), key=lambda x: -x[1])
            ],
            monthly_spend=[
                {"month": k, "total_spend": v}
                for k, v in sorted(monthly_spend.items())
            ],
        )

    def get_po_by_supplier(self, supplier_id: str, limit: int = 10) -> list[dict]:
        """Used by agent tools."""
        pos = (
            self.db.query(PurchaseOrder)
            .filter(PurchaseOrder.supplier_id == supplier_id)
            .order_by(desc(PurchaseOrder.po_date))
            .limit(limit)
            .all()
        )
        return [
            {
                "po_id": po.po_id,
                "item_description": po.item_description,
                "amount": float(po.amount),
                "currency": po.currency,
                "status": po.status,
                "date": po.po_date.isoformat(),
                "category": po.category,
            }
            for po in pos
        ]

    def get_top_suppliers_by_spend(self, limit: int = 5) -> list[dict]:
        """Used by agent tools."""
        rows = (
            self.db.query(
                PurchaseOrder.supplier_id,
                Supplier.supplier_name,
                func.sum(PurchaseOrder.amount).label("total"),
            )
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.supplier_id)
            .group_by(PurchaseOrder.supplier_id, Supplier.supplier_name)
            .order_by(desc("total"))
            .limit(limit)
            .all()
        )
        return [
            {"supplier_id": r.supplier_id, "supplier_name": r.supplier_name, "total_spend": float(r.total)}
            for r in rows
        ]
