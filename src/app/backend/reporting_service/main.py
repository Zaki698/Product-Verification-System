from datetime import date
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import *
from backend.common.db import init_db
from backend.common.schemas import ReportSummary
from backend.reporting_service.helper import query_validation_logs
from backend.reporting_service.agent import reporting_agent

from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

runner = InMemoryRunner(agent=reporting_agent, app_name="pvs_reporting")

app = FastAPI(title="PVS - Reporting Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "reporting", "version": "1.0.0"}


@app.get("/report", response_model=ReportSummary)
async def get_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")

    data = query_validation_logs(start_date.isoformat(), end_date.isoformat())

    session = await runner.session_service.create_session(app_name="pvs_reporting", user_id="qa_manager")
    message = Content(role="user",parts=[Part(text=str(data))])
    events = runner.run(user_id="qa_manager",session_id=session.id,new_message=message)
    for event in events:
        if event.is_final_response():
            reply_text = event.content.parts[0].text

    return ReportSummary(
        start_date=start_date,
        end_date=end_date,
        total_checks=data["total_checks"],
        correct=data["correct"],
        incorrect=data["incorrect"],
        not_found=data["not_found"],
        mfg_date_incorrect=data["mfg_date_incorrect"],
        expiry_date_incorrect=data["expiry_date_incorrect"],
        logs=data["logs"],
        narrative=reply_text
    )


if __name__ == "__main__":
    uvicorn.run("backend.reporting_service.main:app",host="0.0.0.0",port=8002,reload=True)
