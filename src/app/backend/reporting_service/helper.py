from datetime import datetime, timedelta
from typing import Any, Dict

from google.adk.agents import Agent
from sqlalchemy import func, select

from backend.common.db import SessionLocal, ValidationLog, init_db


def query_validation_logs(start_date: str, end_date: str) -> Dict[str, Any]:
    """Fetch all validation log rows and aggregated counts within [start_date, end_date]
    (inclusive), using the indexed checked_at column for speed on large tables.

    Args:
        start_date: ISO date string, e.g. '2026-01-01'
        end_date:   ISO date string, e.g. '2026-01-31'
    """
    init_db()
    db = SessionLocal()
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)

        overall_counts = db.execute(
            select(ValidationLog.result, func.count(ValidationLog.id))
            .where(ValidationLog.checked_at >= start_dt, ValidationLog.checked_at < end_dt)
            .group_by(ValidationLog.result)
        ).all()
        count_map = {r: c for r, c in overall_counts}

        mfg_incorrect = db.execute(
            select(func.count(ValidationLog.id))
            .where(
                ValidationLog.checked_at >= start_dt,
                ValidationLog.checked_at < end_dt,
                ValidationLog.mfg_date_result == "INCORRECT",
            )
        ).scalar() or 0

        expiry_incorrect = db.execute(
            select(func.count(ValidationLog.id))
            .where(
                ValidationLog.checked_at >= start_dt,
                ValidationLog.checked_at < end_dt,
                ValidationLog.expiry_date_result == "INCORRECT",
            )
        ).scalar() or 0

        # Detail rows 
        rows = db.execute(
            select(ValidationLog)
            .where(ValidationLog.checked_at >= start_dt, ValidationLog.checked_at < end_dt)
            .order_by(ValidationLog.checked_at.desc())
            .limit(5000)
        ).scalars().all()

        return {
            "total_checks": sum(count_map.values()),
            "correct": count_map.get("CORRECT", 0),
            "incorrect": count_map.get("INCORRECT", 0),
            "not_found": count_map.get("NOT_FOUND", 0),
            "mfg_date_incorrect": mfg_incorrect,
            "expiry_date_incorrect": expiry_incorrect,
            "logs": [
                {
                    "id": r.id,
                    "wid": r.wid,
                    "ean": r.ean,
                    "manufacturing_date": r.manufacturing_date.isoformat() if r.manufacturing_date else None,
                    "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None,
                    "operator_id": r.operator_id,
                    "result": r.result,
                    "mfg_date_result": r.mfg_date_result,
                    "expiry_date_result": r.expiry_date_result,
                    "validation_mode": r.validation_mode,
                    "ocr_mfg_date": r.ocr_mfg_date,
                    "ocr_expiry_date": r.ocr_expiry_date,
                    "image_path": r.image_path,
                    "checked_at": r.checked_at.isoformat(),
                }
                for r in rows
            ],
        }
    finally:
        db.close()


def summarize_report(
    total_checks: int,
    correct: int,
    incorrect: int,
    not_found: int,
    mfg_date_incorrect: int = 0,
    expiry_date_incorrect: int = 0,
) -> str:
    """Build a short, actionable narrative for the QA manager from the report counts."""
    if total_checks == 0:
        return "No verification activity was recorded in this date range."

    incorrect_rate = (incorrect / total_checks) * 100
    msg = (
        f"{total_checks} verification(s) recorded: "
        f"{correct} correct, {incorrect} incorrect, {not_found} not found."
    )
    if mfg_date_incorrect > 0 or expiry_date_incorrect > 0:
        msg += (
            f" Field breakdown — manufacturing date mismatches: {mfg_date_incorrect}, "
            f"expiry date mismatches: {expiry_date_incorrect}."
        )
    if incorrect_rate >= 10:
        msg += (
            f" ⚠️  Incorrect rate is {incorrect_rate:.1f}%, which is high "
            f"and may warrant investigation."
        )
    elif incorrect > 0:
        msg += f" Incorrect rate: {incorrect_rate:.1f}%."
    else:
        msg += " All checked items matched system records."
    return msg