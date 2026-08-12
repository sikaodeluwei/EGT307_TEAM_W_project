import os
import logging
from fastapi import FastAPI, HTTPException, status
import httpx

# Import existing schemas
from .schemas import TelemetryInput

app = FastAPI(title="AutoCare AI - API Gateway")

# Configure Service URLs via environment variables with defaults
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8002")
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://127.0.0.1:8001")

# Standard HTTP client timeout (10 seconds)
HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

logger = logging.getLogger("api_gateway")

@app.post("/predict")
async def predict_maintenance(telemetry: TelemetryInput):
    # Prepare payload from telemetry input
    telemetry_payload = telemetry.model_dump()

    # Step 1: Forward validated telemetry to AI Inference Service
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            ai_response = await client.post(
                f"{AI_SERVICE_URL}/predict",
                json=telemetry_payload
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI Inference Service timed out."
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to AI Inference Service: {str(exc)}"
            )

    if ai_response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Inference Service returned error code {ai_response.status_code}: {ai_response.text}"
        )

    try:
        ai_data = ai_response.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Received invalid JSON response from AI Inference Service."
        )

    # Step 2: Save prediction record to Database Service
    db_payload = {
        "input_data": telemetry_payload,
        "maintenance_decision": ai_data.get("maintenance_decision"),
        "confidence_score": ai_data.get("confidence_score"),
        "identified_issues": ai_data.get("identified_issues", []),
        "recommendation": ai_data.get("recommendation", None),
        "model_version": ai_data.get("model_version", None)
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            db_response = await client.post(
                f"{DATABASE_SERVICE_URL}/records",
                json=db_payload
            )
            if db_response.status_code not in (status.HTTP_200_OK, status.HTTP_201_CREATED):
                logger.warning(f"Database Service returned non-2xx status: {db_response.status_code}")
        except httpx.TimeoutException:
            logger.error("Database Service timed out while saving record.")
        except httpx.RequestError as exc:
            logger.error(f"Failed to connect to Database Service: {str(exc)}")

    # Return actual AI response back to the caller
    return ai_data


@app.get("/history")
async def get_history():
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            db_response = await client.get(f"{DATABASE_SERVICE_URL}/records")
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database Service timed out."
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to Database Service: {str(exc)}"
            )

    if db_response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Database Service returned error code {db_response.status_code}: {db_response.text}"
        )

    return db_response.json()
