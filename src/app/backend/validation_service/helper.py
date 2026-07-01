
from datetime import datetime
from typing import Any, Dict, Optional

from backend.common.db import Product, SessionLocal, ValidationLog, init_db


def lookup_wid(wid: str) -> Dict[str, Any]:
    """Look up a physical item by its Warehouse ID (WID).

    Args:
        wid: the unique warehouse id scanned / entered by the operator.
    Returns:
        dict with found flag and EAN / manufacturing_date / expiry_date if found.
    """
    init_db()
    db = SessionLocal()
    try:
        product = db.get(Product, wid.strip())
        if not product:
            return {"found": False, "wid": wid}
        return {
            "found": True,
            "wid": product.wid,
            "ean": product.ean,
            "manufacturing_date": product.manufacturing_date.isoformat(),
            "expiry_date": product.expiry_date.isoformat(),
        }
    finally:
        db.close()


def log_validation(
    wid: str,
    mfg_date_result: str,
    expiry_date_result: str,
    operator_id: str = "operator",
    validation_mode: str = "MANUAL",
    ocr_mfg_date: Optional[str] = None,
    ocr_expiry_date: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist an operator's per-field validation decision for a WID.

    The overall 'result' is derived automatically:
      - NOT_FOUND  if WID is not in the system
      - CORRECT    if both mfg_date_result and expiry_date_result are CORRECT
      - INCORRECT  if either field is INCORRECT

    Args:
        wid:               Warehouse ID being checked.
        mfg_date_result:   'CORRECT' or 'INCORRECT' for the manufacturing date.
        expiry_date_result: 'CORRECT' or 'INCORRECT' for the expiry date.
        operator_id:       Identifier of the operator performing the check.
        validation_mode:   'MANUAL' or 'IMAGE'.
        ocr_mfg_date:      ISO date string extracted by AI (image mode only).
        ocr_expiry_date:   ISO date string extracted by AI (image mode only).
        image_path:        Path to the saved inspection photo (if any).
    """
    init_db()
    db = SessionLocal()
    try:
        product = db.get(Product, wid.strip())

        # Derive overall result
        if not product:
            overall_result = "NOT_FOUND"
        elif mfg_date_result == "CORRECT" and expiry_date_result == "CORRECT":
            overall_result = "CORRECT"
        else:
            overall_result = "INCORRECT"

        log = ValidationLog(
            wid=wid.strip(),
            ean=product.ean if product else None,
            manufacturing_date=product.manufacturing_date if product else None,
            expiry_date=product.expiry_date if product else None,
            operator_id=operator_id,
            result=overall_result,
            mfg_date_result=mfg_date_result if product else None,
            expiry_date_result=expiry_date_result if product else None,
            validation_mode=validation_mode,
            ocr_mfg_date=ocr_mfg_date,
            ocr_expiry_date=ocr_expiry_date,
            image_path=image_path,
            checked_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return {"logged": True, "log_id": log.id, "overall_result": overall_result}
    finally:
        db.close()
