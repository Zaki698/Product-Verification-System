import os
from datetime import date, datetime

from sqlalchemy import (create_engine, Column, String, Date, DateTime, BigInteger, Integer, Enum)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_USER = os.getenv("MYSQL_USER", "myuser")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "mypassword")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE", "mydatabase")

DATABASE_URL = (f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    wid = Column(String(64), primary_key=True)
    ean = Column(String(32), nullable=False, index=True)
    manufacturing_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    uploaded_by = Column(String(64), default="warehouse_manager")
    total_rows = Column(Integer, default=0)
    inserted_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    status = Column(Enum("processing", "completed", "failed"), default="processing")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class ValidationLog(Base):
    __tablename__ = "validation_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    wid = Column(String(64), nullable=False, index=True)
    ean = Column(String(32), nullable=True)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    operator_id = Column(String(64), nullable=False, default="operator")
    result = Column(Enum("CORRECT", "INCORRECT", "NOT_FOUND"), nullable=False)
    mfg_date_result = Column(Enum("CORRECT", "INCORRECT"), nullable=True)
    expiry_date_result = Column(Enum("CORRECT", "INCORRECT"), nullable=True)
    validation_mode = Column(Enum("MANUAL", "IMAGE"), nullable=False, default="MANUAL")
    ocr_mfg_date = Column(String(20), nullable=True)
    ocr_expiry_date = Column(String(20), nullable=True)
    image_path = Column(String(512), nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)


def init_db():
    """Create all tables if they don't already exist (idempotent)."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
