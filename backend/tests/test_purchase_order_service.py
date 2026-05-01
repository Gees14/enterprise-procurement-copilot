"""
Tests for PurchaseOrderService using an in-memory SQLite database.
No PostgreSQL or Docker required.
"""
from datetime import datetime

import pytest

from app.db.models import PurchaseOrder, Supplier
from app.services.purchase_order_service import PurchaseOrderService


def _now():
    return datetime.utcnow()


def make_supplier(supplier_id, supplier_name=None):
    return Supplier(
        supplier_id=supplier_id,
        supplier_name=supplier_name or f"Supplier {supplier_id}",
        country="USA",
        risk_level="LOW",
        approved_status=True,
        created_at=_now(),
        updated_at=_now(),
    )


def make_po(
    po_id,
    supplier_id,
    amount,
    status="OPEN",
    category="Equipment",
    po_date=None,
):
    return PurchaseOrder(
        po_id=po_id,
        supplier_id=supplier_id,
        item_description="Test item",
        category=category,
        amount=amount,
        currency="USD",
        po_date=po_date or datetime(2024, 1, 15),
        status=status,
        created_at=_now(),
    )


@pytest.fixture
def seeded_db(db):
    """Two suppliers with four POs across different dates, statuses, and categories."""
    db.add(make_supplier("SUP-001", "Acme Industrial"))
    db.add(make_supplier("SUP-002", "Tech Components"))
    db.add(make_po("PO-001", "SUP-001", 10_000.00, status="CLOSED", category="Raw Materials",
                   po_date=datetime(2024, 1, 15)))
    db.add(make_po("PO-002", "SUP-001", 5_000.00, status="OPEN", category="Safety Equipment",
                   po_date=datetime(2024, 2, 10)))
    db.add(make_po("PO-003", "SUP-002", 45_000.00, status="OPEN", category="Electronics",
                   po_date=datetime(2024, 1, 22)))
    db.add(make_po("PO-004", "SUP-002", 20_000.00, status="CANCELLED", category="Electronics",
                   po_date=datetime(2024, 3, 5)))
    db.commit()
    return db


class TestListPurchaseOrders:
    def test_empty_db(self, db):
        assert PurchaseOrderService(db).list_purchase_orders() == []

    def test_returns_all(self, seeded_db):
        result = PurchaseOrderService(seeded_db).list_purchase_orders()
        assert len(result) == 4

    def test_filter_by_supplier_id(self, seeded_db):
        result = PurchaseOrderService(seeded_db).list_purchase_orders(supplier_id="SUP-001")
        assert len(result) == 2
        assert all(po.supplier_id == "SUP-001" for po in result)

    def test_filter_by_status_case_insensitive(self, seeded_db):
        result = PurchaseOrderService(seeded_db).list_purchase_orders(status="open")
        assert len(result) == 2
        assert all(po.status == "OPEN" for po in result)

    def test_results_ordered_by_date_descending(self, seeded_db):
        result = PurchaseOrderService(seeded_db).list_purchase_orders()
        dates = [po.po_date for po in result]
        assert dates == sorted(dates, reverse=True)

    def test_pagination(self, seeded_db):
        page1 = PurchaseOrderService(seeded_db).list_purchase_orders(limit=2)
        page2 = PurchaseOrderService(seeded_db).list_purchase_orders(skip=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        ids1 = {po.po_id for po in page1}
        ids2 = {po.po_id for po in page2}
        assert ids1.isdisjoint(ids2)


class TestAnalytics:
    def test_empty_db_returns_zeroes(self, db):
        analytics = PurchaseOrderService(db).get_analytics()
        assert analytics.total_spend == 0.0
        assert analytics.total_orders == 0
        assert analytics.open_orders == 0
        assert analytics.closed_orders == 0
        assert analytics.cancelled_orders == 0
        assert analytics.top_suppliers == []
        assert analytics.spend_by_category == []
        assert analytics.monthly_spend == []

    def test_total_spend(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        # 10000 + 5000 + 45000 + 20000 = 80000
        assert analytics.total_spend == pytest.approx(80_000.0)

    def test_total_order_count(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        assert analytics.total_orders == 4

    def test_status_counts(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        assert analytics.open_orders == 2
        assert analytics.closed_orders == 1
        assert analytics.cancelled_orders == 1

    def test_top_suppliers_ordered_by_spend(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        # SUP-002: 45000 + 20000 = 65000; SUP-001: 10000 + 5000 = 15000
        assert len(analytics.top_suppliers) == 2
        assert analytics.top_suppliers[0]["supplier_id"] == "SUP-002"
        assert analytics.top_suppliers[0]["total_spend"] == pytest.approx(65_000.0)
        assert analytics.top_suppliers[1]["supplier_id"] == "SUP-001"
        assert analytics.top_suppliers[1]["total_spend"] == pytest.approx(15_000.0)

    def test_spend_by_category(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        cats = {c["category"]: c["total_spend"] for c in analytics.spend_by_category}
        assert cats["Electronics"] == pytest.approx(65_000.0)
        assert cats["Raw Materials"] == pytest.approx(10_000.0)
        assert cats["Safety Equipment"] == pytest.approx(5_000.0)

    def test_spend_by_category_sorted_descending(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        totals = [c["total_spend"] for c in analytics.spend_by_category]
        assert totals == sorted(totals, reverse=True)

    def test_monthly_spend_keys_and_values(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        months = {m["month"]: m["total_spend"] for m in analytics.monthly_spend}
        # Jan: 10000 (PO-001) + 45000 (PO-003) = 55000
        assert months["2024-01"] == pytest.approx(55_000.0)
        # Feb: 5000 (PO-002)
        assert months["2024-02"] == pytest.approx(5_000.0)
        # Mar: 20000 (PO-004)
        assert months["2024-03"] == pytest.approx(20_000.0)

    def test_monthly_spend_sorted_chronologically(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        months = [m["month"] for m in analytics.monthly_spend]
        assert months == sorted(months)

    def test_top_suppliers_includes_supplier_name(self, seeded_db):
        analytics = PurchaseOrderService(seeded_db).get_analytics()
        names = {s["supplier_id"]: s["supplier_name"] for s in analytics.top_suppliers}
        assert names["SUP-001"] == "Acme Industrial"
        assert names["SUP-002"] == "Tech Components"


class TestAgentTools:
    def test_get_po_by_supplier_returns_dicts(self, seeded_db):
        result = PurchaseOrderService(seeded_db).get_po_by_supplier("SUP-001")
        assert len(result) == 2
        for item in result:
            assert isinstance(item["amount"], float)
            assert "po_id" in item
            assert "status" in item
            assert item["po_id"].startswith("PO-")

    def test_get_po_by_supplier_respects_limit(self, seeded_db):
        result = PurchaseOrderService(seeded_db).get_po_by_supplier("SUP-001", limit=1)
        assert len(result) == 1

    def test_get_po_by_supplier_not_found(self, seeded_db):
        result = PurchaseOrderService(seeded_db).get_po_by_supplier("SUP-999")
        assert result == []

    def test_get_top_suppliers_by_spend_ranking(self, seeded_db):
        result = PurchaseOrderService(seeded_db).get_top_suppliers_by_spend(limit=5)
        assert len(result) == 2
        assert result[0]["supplier_id"] == "SUP-002"
        assert result[0]["total_spend"] == pytest.approx(65_000.0)

    def test_get_top_suppliers_respects_limit(self, seeded_db):
        result = PurchaseOrderService(seeded_db).get_top_suppliers_by_spend(limit=1)
        assert len(result) == 1
        assert result[0]["supplier_id"] == "SUP-002"
