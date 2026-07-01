import csv
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.dialects.mysql import insert as mysql_insert

from backend.common.db import SessionLocal, Product, IngestionBatch, init_db

CHUNK_SIZE = 5000 


def _parse_date(value: str):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value!r}")


def bulk_load_csv(file_path: str, file_name: str, uploaded_by: str = "warehouse_manager") -> Dict[str, Any]:
    """Tool: streams a CSV file from disk and bulk-upserts it into the `products`
    table in fixed-size chunks so that multi-million row files do not blow up
    memory. Duplicate WIDs (already in DB or repeated in-file) are reported,
    not silently overwritten, to protect data integrity.

    Args:
        file_path: absolute path to the CSV file on disk.
        file_name: original file name (for audit logging).
        uploaded_by: identifier of the warehouse manager performing the upload.

    Returns:
        dict summary: batch_id, total_rows, inserted_rows, duplicate_rows, failed_rows, status
    """
    init_db()
    db = SessionLocal()
    batch = IngestionBatch(file_name=file_name, uploaded_by=uploaded_by, status="processing")
    db.add(batch)
    db.commit()
    db.refresh(batch)

    total = inserted = duplicates = failed = 0
    seen_wids_in_file = set()
    buffer = []

    def flush_buffer():
        nonlocal inserted, duplicates
        if not buffer:
            return
        
        stmt = mysql_insert(Product).values(buffer)
        stmt = stmt.on_duplicate_key_update(wid=Product.wid) 
        result = db.execute(stmt)
        db.commit()
        affected = result.rowcount
        clean_inserts = max(0, (2 * len(buffer)) - affected)
        dup_count = len(buffer) - clean_inserts
        inserted += clean_inserts
        duplicates += dup_count
        buffer.clear()

    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required_cols = {"WID", "EAN", "Manufacturing_Date", "Expiry_Date"}
            missing = required_cols - set(c.strip() for c in (reader.fieldnames or []))
            if missing:
                batch.status = "failed"
                batch.finished_at = datetime.utcnow()
                db.commit()
                return {
                    "batch_id": batch.id, "total_rows": 0, "inserted_rows": 0,
                    "duplicate_rows": 0, "failed_rows": 0, "status": "failed",
                    "error": f"Missing required columns: {missing}",
                }

            for row in reader:
                total += 1
                try:
                    wid = row["WID"].strip()
                    ean = row["EAN"].strip()
                    if not wid or not ean:
                        raise ValueError("WID/EAN cannot be empty")
                    if wid in seen_wids_in_file:
                        duplicates += 1
                        continue
                    seen_wids_in_file.add(wid)
                    mfg = _parse_date(row["Manufacturing_Date"])
                    exp = _parse_date(row["Expiry_Date"])
                    buffer.append({
                        "wid": wid, "ean": ean,
                        "manufacturing_date": mfg, "expiry_date": exp,
                    })
                except Exception:
                    failed += 1
                    continue

                if len(buffer) >= CHUNK_SIZE:
                    flush_buffer()

            flush_buffer()

        batch.total_rows = total
        batch.inserted_rows = inserted
        batch.duplicate_rows = duplicates
        batch.failed_rows = failed
        batch.status = "completed"
        batch.finished_at = datetime.utcnow()
        db.commit()

        return {
            "batch_id": batch.id, "total_rows": total, "inserted_rows": inserted,
            "duplicate_rows": duplicates, "failed_rows": failed, "status": "completed",
        }
    except Exception as e:
        batch.status = "failed"
        batch.finished_at = datetime.utcnow()
        db.commit()
        return {
            "batch_id": batch.id, "total_rows": total, "inserted_rows": inserted,
            "duplicate_rows": duplicates, "failed_rows": failed, "status": "failed",
            "error": str(e),
        }
    finally:
        db.close()