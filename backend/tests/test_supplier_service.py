"""
Tests for SupplierService using an in-memory SQLite database.
No PostgreSQL or Docker required.
"""
from datetime import datetime

import pytest

from app.db.models import PurchaseOrder, Supplier
from app.services.supplier_service import SupplierService


def _now():
    return datetime.utcnow()


def make_supplier(
    supplier_id="SUP-001",
    risk_level="LOW",
    approved_status=True,
    supplier_name=None,
    country="USA",
):
    return Supplier(
        supplier_id=supplier_id,
        supplier_name=supplier_name or f"Supplier {supplier_id}",
        country=country,
        risk_level=risk_level,
        approved_status=approved_status,
        created_at=_now(),
        updated_at=_now(),
    )


def make_po(po_id, supplier_id, amount, status="OPEN", category="Equipment"):
    return PurchaseOrder(
        po_id=po_id,
        supplier_id=supplier_id,
        item_description="Test item",
        category=category,
        amount=amount,
        currency="USD",
        po_date=datetime(2024, 1, 15),
        status=status,
        created_at=_now(),
    )


class TestListSuppliers:
    def test_empty_db(self, db):
        service = SupplierService(db)
        assert service.list_suppliers() == []

    def test_returns_all_suppliers(self, db):
        db.add(make_supplier("SUP-001"))
        db.add(make_supplier("SUP-002"))
        db.commit()
        result = SupplierService(db).list_suppliers()
        assert len(result) == 2

    def test_filter_by_risk_level_case_insensitive(self, db):
        db.add(make_supplier("SUP-001", risk_level="LOW"))
        db.add(make_supplier("SUP-002", risk_level="HIGH"))
        db.commit()
        result = SupplierService(db).list_suppliers(risk_level="low")
        assert len(result) == 1
        assert result[0].supplier_id == "SUP-001"

    def test_filter_by_approved_true(self, db):
        db.add(make_supplier("SUP-001", approved_status=True))
        db.add(make_supplier("SUP-002", approved_status=False))
        db.commit()
        result = SupplierService(db).list_suppliers(approved=True)
        assert len(result) == 1
        assert result[0].approved_status is True

    def test_filter_by_approved_false(self, db):
        db.add(make_supplier("SUP-001", approved_status=True))
        db.add(make_supplier("SUP-002", approved_status=False))
        db.commit()
        result = SupplierService(db).list_suppliers(approved=False)
        assert len(result) == 1
        assert result[0].approved_status is False

    def test_pagination_skip_and_limit(self, db):
        for i in range(5):
            db.add(make_supplier(f"SUP-00{i + 1}"))
        db.commit()
        page1 = SupplierService(db).list_suppliers(limit=2)
        page2 = SupplierService(db).list_suppliers(skip=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert {r.supplier_id for r in page1}.isdisjoint({r.supplier_id for r in page2})


class TestSupplierDetail:
    def test_not_found_returns_none(self, db):
        assert SupplierService(db).get_supplier_detail("SUP-999") is None

    def test_detail_no_purchase_orders(self, db):
        db.add(make_supplier("SUP-001"))
        db.commit()
        detail = SupplierService(db).get_supplier_detail("SUP-001")
        assert detail is not None
        assert detail.supplier_id == "SUP-001"
        assert detail.total_po_amount == 0.0
        assert detail.po_count == 0
        assert detail.open_po_count == 0

    def test_detail_aggregates_po_totals(self, db):
        db.add(make_supplier("SUP-001"))
        db.add(make_po("PO-001", "SUP-001", 10_000.00, status="OPEN"))
        db.add(make_po("PO-002", "SUP-001", 5_000.00, status="CLOSED"))
        db.commit()
        detail = SupplierService(db).get_supplier_detail("SUP-001")
        assert detail.total_po_amount == pytest.approx(15_000.0)
        assert detail.po_count == 2
        assert detail.open_po_count == 1

    def test_detail_only_counts_open_pos(self, db):
        db.add(make_supplier("SUP-001"))
        db.add(make_po("PO-001", "SUP-001", 1_000.00, status="CLOSED"))
        db.add(make_po("PO-002", "SUP-001", 1_000.00, status="CANCELLED"))
        db.commit()
        detail = SupplierService(db).get_supplier_detail("SUP-001")
        assert detail.open_po_count == 0

    def test_detail_does_not_leak_other_suppliers_pos(self, db):
        db.add(make_supplier("SUP-001"))
        db.add(make_supplier("SUP-002"))
        db.add(make_po("PO-001", "SUP-001", 50_000.00))
        db.add(make_po("PO-002", "SUP-002", 99_000.00))
        db.commit()
        detail = SupplierService(db).get_supplier_detail("SUP-001")
        assert detail.total_po_amount == pytest.approx(50_000.0)
        assert detail.po_count == 1


class TestSupplierProfileDict:
    def test_returns_dict_with_correct_id(self, db):
        db.add(make_supplier("SUP-001", supplier_name="Acme Corp"))
        db.commit()
        result = SupplierService(db).get_supplier_profile_dict("SUP-001")
        assert isinstance(result, dict)
        assert result["supplier_id"] == "SUP-001"
        assert result["supplier_name"] == "Acme Corp"

    def test_not_found_returns_none(self, db):
        assert SupplierService(db).get_supplier_profile_dict("SUP-999") is None

    def test_dict_includes_po_metrics(self, db):
        db.add(make_supplier("SUP-001"))
        db.add(make_po("PO-001", "SUP-001", 7_500.00, status="OPEN"))
        db.commit()
        result = SupplierService(db).get_supplier_profile_dict("SUP-001")
        assert result["total_po_amount"] == pytest.approx(7_500.0)
        assert result["po_count"] == 1
        assert result["open_po_count"] == 1
