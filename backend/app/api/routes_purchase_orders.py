from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.purchase_orders import PurchaseOrderOut, POAnalytics
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> PurchaseOrderService:
    return PurchaseOrderService(db)


@router.get("", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    supplier_id: str | None = None,
    status: str | None = None,
    service: PurchaseOrderService = Depends(get_service),
):
    return service.list_purchase_orders(
        skip=skip, limit=limit, supplier_id=supplier_id, status=status
    )


@router.get("/analytics", response_model=POAnalytics)
def get_analytics(service: PurchaseOrderService = Depends(get_service)):
    return service.get_analytics()
