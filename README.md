# AutoCare AI: Smart Vehicle Maintenance Prediction System

AutoCare AI is an EGT307 AI Applications Development project that analyses vehicle telemetry and predicts the required vehicle maintenance level. The project uses four independent microservices so the interface, request routing, model inference, and prediction storage can be developed and deployed separately.

## Prediction classes

The trained model uses the labels found in `test_data.xlsx`:

- `Safe for Driving`
- `At Risk`
- `Needs Immediate Maintenance`

The Dashboard displays the decision returned by the API Gateway without replacing or remapping it. The Database stores the decision exactly as submitted.

## Project objectives

- Predict a vehicle's maintenance condition from telemetry data.
- Show the prediction confidence and possible maintenance issues.
- Help vehicle owners, technicians, workshops, and fleet operators identify risks earlier.
- Store prediction history for later review.
- Demonstrate a modular, containerised, and scalable AI application.

## Architecture

The intended prediction flow is:

```text
User -> Dashboard -> API Gateway -> AI Inference
                                -> Database
     <- Dashboard <- API Gateway
```

Prediction history follows `Dashboard -> API Gateway -> Database -> API Gateway -> Dashboard`. The Dashboard does not communicate directly with the AI Inference or Database services.

| Microservice | Technology | Responsibility | Port |
|---|---|---|---:|
| Dashboard Service | Streamlit | Collect telemetry and display predictions/history | 8501 |
| API Gateway Service | FastAPI | Validate and coordinate service requests | 8000 |
| AI Inference Service | FastAPI, scikit-learn | Load the trained model and return predictions | 8000 |
| Database Service | FastAPI, SQLite | Store and retrieve prediction history | 8000 |

The AI Inference Service is the planned horizontal-scaling target. The architecture diagram and detailed explanation are under `system architect/`.

## Telemetry schema

All services use the exact field names defined by the API Gateway and AI Inference Service:

- `Car_Model`
- `Vehicle_Age_Years`
- `Total_Mileage_KM`
- `Tire_Pressure_PSI`
- `Engine_RPM`
- `Battery_Voltage_V`
- `Fuel_Level_Percent`
- `Coolant_Temperature_C`
- `Brake_Pad_Thickness_mm`
- `O2_Sensor_Voltage_V`

## Dataset and model

`test_data.xlsx` contains 2,500 simulated telemetry records in the `Telemetry Data` sheet. It contains the ten model features, a `Car_Plate` identifier excluded during training, and the `Maintenance_Decision` target. The saved Random Forest preprocessing pipeline is `services/ai_inference_service/vehicle_maintenance_model.pkl`.

The dataset and trained model are not changed by the Dashboard or Database implementation.

## Local setup

Run these commands from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r services\database_service\requirements.txt
python -m pip install -r services\dashboard_service\requirements.txt
python -m pip install pytest httpx
```

Start the Database Service:

```powershell
$env:DATABASE_PATH = "services\database_service\data\autocare.db"
python -m uvicorn services.database_service.app:app --host 127.0.0.1 --port 8001
```

The Database API is available at `http://127.0.0.1:8001/docs` and provides:

- `GET /health`
- `POST /records`
- `GET /records`
- `GET /records/{record_id}`

Start the Dashboard Service in another PowerShell window:

```powershell
$env:API_GATEWAY_URL = "http://127.0.0.1:8000"
python -m streamlit run services\dashboard_service\app.py --server.port 8501
```

Open `http://127.0.0.1:8501`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest services\database_service\tests services\dashboard_service\tests -v
.\.venv\Scripts\python.exe -m compileall -q services
```

## Docker

Each completed owned microservice has its own Dockerfile and requirements file.

Build the Database image:

```powershell
docker build -t autocare-database:latest services\database_service
docker run --rm -p 8001:8000 -v autocare-db-data:/data autocare-database:latest
```

Build the Dashboard image:

```powershell
docker build -t autocare-dashboard:latest services\dashboard_service
docker run --rm -p 8501:8501 -e API_GATEWAY_URL=http://host.docker.internal:8000 autocare-dashboard:latest
```

A full four-service `docker-compose.yml` is not included yet because the API Gateway and AI Inference services do not have Dockerfiles. When those are added, internal URLs should be:

- Dashboard: `API_GATEWAY_URL=http://api-gateway:8000`
- API Gateway: `AI_SERVICE_URL=http://ai-inference:8000`
- API Gateway: `DATABASE_SERVICE_URL=http://database:8000`

## Kubernetes and Minikube

The current manifests cover the owned services:

- `k8s/database.yaml`: PersistentVolumeClaim, Database Deployment, and internal ClusterIP Service.
- `k8s/dashboard.yaml`: Dashboard Deployment and NodePort Service.

After installing and starting Minikube, build the two images in Minikube's Docker environment and apply the manifests:

```powershell
minikube start
minikube docker-env --shell powershell | Invoke-Expression
docker build -t autocare-database:latest services\database_service
docker build -t autocare-dashboard:latest services\dashboard_service
kubectl apply -f k8s\database.yaml
kubectl apply -f k8s\dashboard.yaml
kubectl get pods,services,pvc
minikube service dashboard-service
```

The complete deployment still requires Kubernetes manifests for the API Gateway and AI Inference Service. The AI Deployment should be horizontally scalable to three replicas, for example:

```powershell
kubectl scale deployment ai-inference --replicas=3
```

Use the exact deployment name selected by the AI service owner.

## Environment variables

| Variable | Service | Local default | Container/Kubernetes value |
|---|---|---|---|
| `API_GATEWAY_URL` | Dashboard | `http://127.0.0.1:8000` | Gateway service URL |
| `DATABASE_PATH` | Database | `services/database_service/data/autocare.db` | `/data/autocare.db` |

## Known integration limitations

The current API Gateway returns a hard-coded prediction. It does not yet call the AI Inference Service, store results in the Database Service, or expose `GET /history`. Until the API teammate completes those routes, the Dashboard will accurately display the gateway's current response and will show a clear message that history is unavailable.

The API Gateway owner still needs to:

1. Read `AI_SERVICE_URL` and `DATABASE_SERVICE_URL` from environment variables.
2. Forward the validated telemetry to the AI service's current `POST /predict` endpoint.
3. Store the returned telemetry and prediction through Database `POST /records`.
4. Add `GET /history` that proxies Database `GET /records`.
5. Preserve the existing request and response field names.
6. Add the API Gateway Dockerfile and Kubernetes Deployment/ClusterIP Service.

The AI owner still needs to add the AI Dockerfile and Kubernetes Deployment/ClusterIP Service, using a deployment design that can be scaled horizontally.
