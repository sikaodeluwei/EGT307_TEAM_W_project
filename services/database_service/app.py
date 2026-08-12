import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class VehicleTelemetryInput(BaseModel):
    Car_Model: str
    Vehicle_Age_Years: float = Field(..., ge=0.0, le=30.0)
    Total_Mileage_KM: int = Field(..., ge=0, le=1_000_000)
    Tire_Pressure_PSI: float = Field(..., ge=10.0, le=60.0)
    Engine_RPM: int = Field(..., ge=0, le=10_000)
    Battery_Voltage_V: float = Field(..., ge=8.0, le=18.0)
    Fuel_Level_Percent: float = Field(..., ge=0.0, le=100.0)
    Coolant_Temperature_C: float = Field(..., ge=0.0, le=150.0)
    Brake_Pad_Thickness_mm: float = Field(..., ge=0.0, le=20.0)
    O2_Sensor_Voltage_V: float = Field(..., ge=0.0, le=2.0)


class PredictionRecordCreate(BaseModel):
    input_data: VehicleTelemetryInput
    maintenance_decision: str = Field(..., min_length=1)
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    identified_issues: List[str]
    recommendation: str | None = None
    model_version: str | None = None


class PredictionRecord(PredictionRecordCreate):
    id: int
    timestamp: datetime


def get_database_path() -> Path:
    default_path = Path(__file__).resolve().parent / "data" / "autocare.db"
    return Path(os.getenv("DATABASE_PATH", str(default_path))).expanduser().resolve()


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                input_data TEXT NOT NULL,
                maintenance_decision TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                identified_issues TEXT NOT NULL,
                recommendation TEXT,
                model_version TEXT
            )
            """
        )


def row_to_record(row: sqlite3.Row) -> PredictionRecord:
    return PredictionRecord(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        input_data=json.loads(row["input_data"]),
        maintenance_decision=row["maintenance_decision"],
        confidence_score=row["confidence_score"],
        identified_issues=json.loads(row["identified_issues"]),
        recommendation=row["recommendation"],
        model_version=row["model_version"],
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="AutoCare AI Database Service",
    description="Stores and retrieves vehicle maintenance prediction history.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"service": "Database Service", "status": "online", "docs_url": "/docs"}


@app.get("/health")
def health_check():
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error

    return {
        "status": "healthy",
        "service": "database_service",
        "database": "connected",
    }


@app.post("/records", response_model=PredictionRecord, status_code=201)
def create_record(record: PredictionRecordCreate):
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO prediction_records (
                    timestamp,
                    input_data,
                    maintenance_decision,
                    confidence_score,
                    identified_issues,
                    recommendation,
                    model_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    record.input_data.model_dump_json(),
                    record.maintenance_decision,
                    record.confidence_score,
                    json.dumps(record.identified_issues),
                    record.recommendation,
                    record.model_version,
                ),
            )
            record_id = cursor.lastrowid
            row = connection.execute(
                "SELECT * FROM prediction_records WHERE id = ?", (record_id,)
            ).fetchone()
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="Could not store prediction record") from error

    return row_to_record(row)


@app.get("/records", response_model=list[PredictionRecord])
def list_records():
    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM prediction_records ORDER BY id DESC"
            ).fetchall()
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="Could not retrieve prediction records") from error

    return [row_to_record(row) for row in rows]


@app.get("/records/{record_id}", response_model=PredictionRecord)
def get_record(record_id: int):
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM prediction_records WHERE id = ?", (record_id,)
            ).fetchone()
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="Could not retrieve prediction record") from error

    if row is None:
        raise HTTPException(status_code=404, detail="Prediction record not found")

    return row_to_record(row)
