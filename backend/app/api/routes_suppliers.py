from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.suppliers import SupplierOut, SupplierDetail
from app.services.supplier_service import SupplierService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> SupplierService:
    return SupplierService(db)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    skip: int = 0,
    limit: int = 50,
    risk_level: str | None = None,
    approved: bool | None = None,
    service: SupplierService = Depends(get_service),
):
    return service.list_suppliers(skip=skip, limit=limit, risk_level=risk_level, approved=approved)


@router.get("/{supplier_id}", response_model=SupplierDetail)
def get_supplier(supplier_id: str, service: SupplierService = Depends(get_service)):
    supplier = service.get_supplier_detail(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    return supplier
