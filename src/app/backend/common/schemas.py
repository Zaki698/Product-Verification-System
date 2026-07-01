from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel


class IngestionResult(BaseModel):
    batch_id: int
    file_name: str
    total_rows: int
    inserted_rows: int
    duplicate_rows: int
    failed_rows: int
    status: str
    message: str


class ProductLookupResponse(BaseModel):
    found: bool
    wid: str
    ean: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    message: str


class ValidationRequest(BaseModel):
    wid: str
    operator_id: str = "operator"
    validation_mode: Literal["MANUAL", "IMAGE"] = "MANUAL"
    mfg_date_result: Literal["CORRECT", "INCORRECT"]
    expiry_date_result: Literal["CORRECT", "INCORRECT"]
    ocr_mfg_date: Optional[str] = None
    ocr_expiry_date: Optional[str] = None
    image_path: Optional[str] = None


class OcrExtractResponse(BaseModel):
    success: bool
    mfg_date: Optional[str] = None
    expiry_date: Optional[str] = None
    confidence: Optional[float] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None


class ValidationLogOut(BaseModel):
    id: int
    wid: str
    ean: Optional[str]
    manufacturing_date: Optional[date]
    expiry_date: Optional[date]
    operator_id: str
    result: str
    mfg_date_result: Optional[str] = None
    expiry_date_result: Optional[str] = None
    validation_mode: Optional[str] = None
    ocr_mfg_date: Optional[str] = None
    ocr_expiry_date: Optional[str] = None
    image_path: Optional[str]
    checked_at: datetime


class ReportRequest(BaseModel):
    start_date: date
    end_date: date


class ReportSummary(BaseModel):
    start_date: date
    end_date: date
    total_checks: int
    correct: int
    incorrect: int
    not_found: int
    mfg_date_incorrect: int
    expiry_date_incorrect: int
    logs: List[ValidationLogOut]
    narrative: str
