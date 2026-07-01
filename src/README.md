# 🏭 Product Verification System (PVS)

> An AI-powered, multi-agent warehouse product verification platform built with **Google ADK**, **FastAPI**, **MySQL**, and **Streamlit**.

---

## Overview

The Product Verification System solves a real warehouse operations problem: verifying that physical product labels (manufacturing dates, expiry dates, barcodes) match what is recorded in the inventory database — at scale, across multiple roles.

Three user roles, three independent services:

| Role | Service | UI Port | API Port |
|---|---|---|---|
| 📦 Warehouse Manager | Ingestion Service | `8501` | `8000` |
| ✅ Warehouse Operator | Validation Service | `8502` | `8001` |
| 📊 QA Manager | Reporting Service | `8503` | `8002` |

**Key capabilities:**
- Bulk CSV ingestion of millions of product records with chunked streaming (no memory blowout)
- On-floor product validation via WID scan — manual or AI-assisted photo upload
- Gemini Vision OCR extracts manufacturing/expiry dates directly from product label images
- Per-field granular logging (manufacturing date verdict + expiry date verdict separately)
- AI-generated executive QA reports via Google ADK agent (narrative, root cause analysis, recommendations)

---

## Architecture

```
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│   Manager UI          │   │   Operator UI         │   │   QA Manager UI      │
│   Streamlit :8501     │   │   Streamlit :8502     │   │   Streamlit :8503    │
└──────────┬───────────┘   └──────────┬────────────┘   └──────────┬───────────┘
           │ HTTP                      │ HTTP                       │ HTTP
           ▼                           ▼                            ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  Ingestion Service   │   │  Validation Service  │   │  Reporting Service   │
│  FastAPI :8000       │   │  FastAPI :8001       │   │  FastAPI :8002       │
│                      │   │                      │   │                      │
│  • bulk_load_csv     │   │  • lookup_wid        │   │  • query_logs        │
│  • chunked insert    │   │  • extract_dates     │   │  • ADK report agent  │
│                      │   │    (Gemini Vision)   │   │    (Gemini 2.5 Flash)│
│                      │   │  • log_validation    │   │                      │
└──────────┬───────────┘   └──────────┬────────────┘   └──────────┬───────────┘
           │                           │                            │
           └───────────────────────────┼────────────────────────────┘
                                       ▼
                              ┌─────────────────┐
                              │   MySQL 8.0      │
                              │  (Docker Desktop)│
                              │                  │
                              │  products        │
                              │  ingestion_      │
                              │    batches       │
                              │  validation_logs │
                              └─────────────────┘
```

### Agent Architecture

```
validation_agent (Google ADK)          reporting_agent (Google ADK)
    └── extract_dates_from_image            └── Gemini 2.5 Flash
        (Gemini Vision tool)                    • Executive Summary
                                                • Quantitative Analysis
                                                • Root Cause Analysis
                                                • Business Impact
                                                • Recommendations
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | [Google ADK] |
| LLM / Vision | Gemini 2.5 Flash |
| Backend | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | MySQL 8.0 (Docker Desktop) |
| DB Driver | PyMySQL |
| Data Validation | Pydantic v2 |
| Frontend | Streamlit |
| Environment | Anaconda (conda) |

---

## Project Structure

```
flipkart_assgnmnt/
├── docker-compose.yml          # MySQL container only
├── test_input.csv              # Sample CSV for ingestion testing
├── test_image.jpg              # Sample product label image for OCR testing
└── app/
    ├── config.py               # API keys (Gemini)
    ├── requirement.txt         # Python dependencies
    ├── schema.sql              # Full DB schema (run once)
    │
    ├── backend/
    │   ├── common/
    │   │   ├── db.py           # SQLAlchemy engine, ORM models, init_db()
    │   │   └── schemas.py      # Pydantic request/response models
    │   │
    │   ├── ingestion_service/
    │   │   ├── main.py         # FastAPI app — port 8000
    │   │   └── helper.py       # bulk_load_csv() — chunked streaming insert
    │   │
    │   ├── validation_service/
    │   │   ├── main.py         # FastAPI app — port 8001
    │   │   ├── agent.py        # Gemini Vision OCR tool
    │   │   ├── helper.py       # lookup_wid(), log_validation()
    │   │   └── prompts.py      # OCR system prompt
    │   │
    │   └── reporting_service/
    │       ├── main.py         # FastAPI app — port 8002
    │       ├── agent.py        # Google ADK reporting_agent definition
    │       ├── helper.py       # query_validation_logs()
    │       └── prompts.py      # Executive report system prompt
    │
    └── frontend/
        ├── manager_ui.py       # Warehouse Manager — CSV upload UI
        ├── operator_ui.py      # Warehouse Operator — floor validation UI
        └── qa_ui.py            # QA Manager — reports + AI narrative UI
```

---

## Prerequisites

Before you start, ensure the following are installed on your machine:

|---|---|---|
| Anaconda / Miniconda |
| Docker Desktop |
| Git |

You will also need a **Google Gemini API key**.

> **Note:** Docker Desktop is used **only for the MySQL database**. All Python services run locally in a conda environment — no full Docker Compose for the app itself.

---

## Development Environment Setup

### 1. Clone the repository

```bash
git clone repo_link
cd product-verification-system
```

### 2. Create and activate the conda environment

```bash
conda create -n pvs python=3.13 -y
conda activate pvs
```

### 3. Install Python dependencies

```bash
cd app
pip install -r requirement.txt
```

### 4. Set your Gemini API key

Open `app/config.py` and replace the placeholder:

```python
# app/config.py
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
```

---

## Database Setup (Docker Desktop)

The MySQL database runs as a single Docker container via Docker Desktop. The application services connect to it on `localhost:3306`.

### 1. Start the MySQL container

From the **root** of the repository (where `docker-compose.yml` lives):

```bash
docker-compose up -d
```

This starts a MySQL 8.0 container named `mysql-db`

Data is persisted in a Docker volume (`mysql-data`) so it survives container restarts.


### 2. Apply the database schema

Wait ~15 seconds for MySQL to finish initialising, then run:

```bash
docker exec -i mysql-db mysql -u myuser -pmypassword mydatabase < app/schema.sql
```


## Running the Application

All commands below assume you are inside the `app/` directory with the `pvs` conda environment active.

```bash
conda activate pvs
cd app
```

> **Important:** All services must be started from the `app/` directory because `backend/` and `frontend/` are resolved relative to it (it acts as the Python path root).

### Start all 6 processes

Open **6 separate terminal windows/tabs**, all with `conda activate pvs` and `cd app`:

**Terminal 1 — Ingestion Service (port 8000)**
```bash
uvicorn backend.ingestion_service.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Validation Service (port 8001)**
```bash
uvicorn backend.validation_service.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 3 — Reporting Service (port 8002)**
```bash
uvicorn backend.reporting_service.main:app --host 0.0.0.0 --port 8002 --reload
```

**Terminal 4 — Manager UI (port 8501)**
```bash
streamlit run frontend/manager_ui.py --server.port 8501
```

**Terminal 5 — Operator UI (port 8502)**
```bash
streamlit run frontend/operator_ui.py --server.port 8502
```

**Terminal 6 — QA Manager UI (port 8503)**
```bash
streamlit run frontend/qa_ui.py --server.port 8503
```

---

### End-to-end test flow

```
1. Start Docker Desktop → ensure mysql-db container is Up
2. Run: docker exec -i mysql-db mysql -u myuser -pmypassword mydatabase < app/schema.sql
3. Start all 6 processes (see above)
4. Open Manager UI (8501) → upload test_input.csv → verify no. of rows inserted
5. Open Operator UI (8502) → look up with WID → validate manually or with image
6. Open QA UI (8503) → generate report → review AI narrative
```

---

## Stopping the Application

**Stop all Python processes:**
Press `Ctrl+C` in each terminal.

**Stop the MySQL container (data is preserved):**
```bash
docker-compose stop
```

**Stop and remove the container (data is preserved in volume):**
```bash
docker-compose down
```

**Stop and remove everything including the database volume** ⚠️:
```bash
docker-compose down -v
```
