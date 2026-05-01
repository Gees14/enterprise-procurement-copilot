"""
Seed script — loads sample CSV data into PostgreSQL and triggers document ingestion.
Run with: python -m app.db.seed
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

from app.core.logging import configure_logging, get_logger
from app.db.database import SessionLocal, create_tables
from app.db.models import Supplier, PurchaseOrder, UnspscCategory

configure_logging()
logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


def seed_suppliers(db) -> int:
    if db.query(Supplier).count() > 0:
        logger.info("Suppliers already seeded — skipping.")
        return 0

    path = DATA_DIR / "sample_suppliers.csv"
    if not path.exists():
        logger.warning("sample_suppliers.csv not found at %s", path)
        return 0

    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db.add(Supplier(
                supplier_id=row["supplier_id"],
                supplier_name=row["supplier_name"],
                country=row["country"],
                risk_level=row["risk_level"],
                approved_status=row["approved_status"].lower() == "true",
                missing_documents=row.get("missing_documents") or None,
                contact_email=row.get("contact_email") or None,
                category=row.get("category") or None,
            ))
            count += 1

    db.commit()
    logger.info("Seeded %d suppliers.", count)
    return count


def seed_purchase_orders(db) -> int:
    if db.query(PurchaseOrder).count() > 0:
        logger.info("Purchase orders already seeded — skipping.")
        return 0

    path = DATA_DIR / "sample_purchase_orders.csv"
    if not path.exists():
        logger.warning("sample_purchase_orders.csv not found at %s", path)
        return 0

    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db.add(PurchaseOrder(
                po_id=row["po_id"],
                supplier_id=row["supplier_id"],
                item_description=row["item_description"],
                category=row.get("category") or None,
                unspsc_code=row.get("unspsc_code") or None,
                amount=float(row["amount"]),
                currency=row.get("currency", "USD"),
                po_date=datetime.fromisoformat(row["po_date"]),
                status=row["status"],
            ))
            count += 1

    db.commit()
    logger.info("Seeded %d purchase orders.", count)
    return count


def seed_unspsc(db) -> int:
    if db.query(UnspscCategory).count() > 0:
        logger.info("UNSPSC categories already seeded — skipping.")
        return 0

    path = DATA_DIR / "sample_unspsc_categories.csv"
    if not path.exists():
        logger.warning("sample_unspsc_categories.csv not found at %s", path)
        return 0

    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            db.add(UnspscCategory(
                category_id=row["category_id"],
                category_name=row["category_name"],
                keywords=row.get("keywords") or None,
                description=row.get("description") or None,
            ))
            count += 1

    db.commit()
    logger.info("Seeded %d UNSPSC categories.", count)
    return count


def main():
    logger.info("Running database seed...")
    create_tables()
    db = SessionLocal()
    try:
        seed_suppliers(db)
        seed_purchase_orders(db)
        seed_unspsc(db)
        logger.info("Seed complete.")
    except Exception as exc:
        logger.error("Seed failed: %s", exc)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
