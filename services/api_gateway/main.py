from fastapi import FastAPI, HTTPException
from schemas import PredictionResponse, VehicleTelemetryInput

app = FastAPI(
    title="EGT307 Vehicle Maintenance API Gateway",
    description="Central API Gateway orchestrating requests between Dashboard UI, AI Inference Service, and Database.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "service": "API Gateway",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "api_gateway"}


@app.post("/predict", response_model=PredictionResponse)
def handle_prediction(telemetry: VehicleTelemetryInput):
    """API Gateway Endpoint: Performs input validation and handles payload orchestration."""
    try:
        data_dict = telemetry.model_dump()

        # Gateway boundary check
        if data_dict["Brake_Pad_Thickness_mm"] < 0:
            raise HTTPException(
                status_code=400, detail="Invalid brake pad thickness."
            )

        return PredictionResponse(
            maintenance_decision="Safe for Driving",
            confidence_score=97.6,
            identified_issues=[
                "All telemetry metrics within standard operating parameters"
            ],
            status="success",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"API Gateway Error: {str(e)}"
        )
