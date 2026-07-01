import base64
import os
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from backend.common.db import init_db
from backend.common.schemas import (OcrExtractResponse,ProductLookupResponse,ValidationRequest)
from backend.validation_service.helper import log_validation,lookup_wid
from backend.validation_service.agent import extract_dates_from_image

app = FastAPI(title="PVS - Validation Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

IMAGE_DIR = os.getenv("IMAGE_DIR", "/tmp/pvs_images")
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")


@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "service": "validation", "version": "1.0.0"}


@app.get("/lookup/{wid}", response_model=ProductLookupResponse)
def lookup(wid: str):
    """Primary-key lookup — sub-millisecond even on a 10M-row products table."""
    result = lookup_wid(wid)
    if not result.get("found"):
        return ProductLookupResponse(found=False, wid=wid, message="WID not found in system.")
    return ProductLookupResponse(
        found=True,
        wid=result["wid"],
        ean=result["ean"],
        manufacturing_date=result["manufacturing_date"],
        expiry_date=result["expiry_date"],
        message="Product found.",
    )


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Save the operator's inspection photo.
    Returns: {image_path, url}
    """
    ext = os.path.splitext(file.filename or "capture")[1] or ".jpg"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(IMAGE_DIR, saved_name)
    content = await file.read()
    with open(saved_path, "wb") as out:
        out.write(content)
    return {"image_path": saved_path, "url": f"/images/{saved_name}"}


@app.post("/extract-dates", response_model=OcrExtractResponse)
async def extract_dates(file: UploadFile = File(...)):
    """Upload a product label image; the AI extracts manufacturing date and
    expiry date from it using Gemini Vision.

    The operator can then review the extracted values, edit if the AI made a
    mistake, and choose CORRECT/INCORRECT per field before submitting.
    """
    image_bytes = await file.read()
    mime_type = file.content_type or "image/jpeg"

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    result = extract_dates_from_image(image_b64=image_b64, mime_type=mime_type)

    return OcrExtractResponse(
        success=result.get("success", False),
        mfg_date=result.get("mfg_date"),
        expiry_date=result.get("expiry_date"),
        confidence=result.get("confidence"),
        raw_text=result.get("raw_text"),
        error=result.get("error"),
    )


@app.post("/validate")
def validate(req: ValidationRequest):
    """Log the operator's validation decision.

    Accepts per-field results (mfg_date_result, expiry_date_result).
    Derives the overall result:
      - CORRECT    if both fields are CORRECT
      - INCORRECT  if either field is INCORRECT
      - NOT_FOUND  if WID doesn't exist in the system

    Also records validation_mode (MANUAL/IMAGE) and any AI-extracted dates
    for analytics purposes.
    """
    if req.mfg_date_result not in ("CORRECT", "INCORRECT"):
        raise HTTPException(
            status_code=400,
            detail="mfg_date_result must be CORRECT or INCORRECT",
        )
    if req.expiry_date_result not in ("CORRECT", "INCORRECT"):
        raise HTTPException(
            status_code=400,
            detail="expiry_date_result must be CORRECT or INCORRECT",
        )

    log_result = log_validation(
        wid=req.wid,
        mfg_date_result=req.mfg_date_result,
        expiry_date_result=req.expiry_date_result,
        operator_id=req.operator_id,
        validation_mode=req.validation_mode,
        ocr_mfg_date=req.ocr_mfg_date,
        ocr_expiry_date=req.ocr_expiry_date,
        image_path=req.image_path,
    )

    return {
        "log_id": log_result["log_id"],
        "wid": req.wid,
        "mfg_date_result": req.mfg_date_result,
        "expiry_date_result": req.expiry_date_result,
        "overall_result": log_result["overall_result"],
        "message": "Validation recorded.",
    }


if __name__ == "__main__":
    uvicorn.run("backend.validation_service.main:app",host="0.0.0.0",port=8001,reload=True)
