import os
import shutil
import tempfile
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from sqlalchemy import select

from backend.common.db import init_db, SessionLocal, IngestionBatch
from backend.common.schemas import IngestionResult
from backend.ingestion_service.helper import bulk_load_csv

app = FastAPI(title="PVS - Ingestion Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/pvs_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "ingestion"}


@app.post("/upload", response_model=IngestionResult)
async def upload_csv(file: UploadFile = File(...)):
    """Bulk-load a product CSV. Designed for very large files: the file is
    streamed to a temp path then read/chunked by bulk_load_csv so the whole
    file is never held in memory at once."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    tmp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        result = bulk_load_csv(tmp_path, file.filename)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    if result.get("status") == "failed" and "error" in result:
        message = f"Failed: {result['error']}"
    else:
        message = (
            f"Loaded {result['inserted_rows']} of {result['total_rows']} rows "
            f"({result['duplicate_rows']} duplicates, {result['failed_rows']} invalid)."
        )

    return IngestionResult(
        batch_id=result["batch_id"],
        file_name=file.filename,
        total_rows=result["total_rows"],
        inserted_rows=result["inserted_rows"],
        duplicate_rows=result["duplicate_rows"],
        failed_rows=result["failed_rows"],
        status=result["status"],
        message=message,
    )


@app.get("/batches")
def list_batches(limit: int = 20):
    db = SessionLocal()
    try:
        rows = db.execute(
            select(IngestionBatch).order_by(IngestionBatch.id.desc()).limit(limit)
        ).scalars().all()
        return [
            {
                "id": r.id, "file_name": r.file_name, "uploaded_by": r.uploaded_by,
                "total_rows": r.total_rows, "inserted_rows": r.inserted_rows,
                "duplicate_rows": r.duplicate_rows, "failed_rows": r.failed_rows,
                "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at,
            }
            for r in rows
        ]
    finally:
        db.close()


@app.get("/batches/{batch_id}")
def get_batch(batch_id: int):
    db = SessionLocal()
    try:
        r = db.get(IngestionBatch, batch_id)
        if not r:
            raise HTTPException(status_code=404, detail="Batch not found")
        return {
            "id": r.id, "file_name": r.file_name, "status": r.status,
            "total_rows": r.total_rows, "inserted_rows": r.inserted_rows,
            "duplicate_rows": r.duplicate_rows, "failed_rows": r.failed_rows,
        }
    finally:
        db.close()


if __name__ == "__main__":
    uvicorn.run("backend.ingestion_service.main:app", host="0.0.0.0", port=8000, reload=True)