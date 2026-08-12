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
| AI Inference Service | FastAPI, scikit-learn | Load the trained model and return predictions | 8001 |
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

Run these commands from the repository root in PowerShell. The service-specific
requirements files keep each microservice's dependencies explicit:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r services\api_gateway\requirements.txt
python -m pip install -r services\ai_inference_service\requirements.txt
python -m pip install -r services\database_service\requirements.txt
python -m pip install -r services\dashboard_service\requirements.txt
python -m pip install pytest httpx
```

Start the four services in separate PowerShell windows, in this order.

Database Service:

```powershell
$env:DATABASE_PATH = "services\database_service\data\autocare.db"
python -m uvicorn services.database_service.app:app --host 127.0.0.1 --port 8001
```

The Database API is available at `http://127.0.0.1:8001/docs` and provides:

- `GET /health`
- `POST /records`
- `GET /records`
- `GET /records/{record_id}`

AI Inference Service:

```powershell
python -m uvicorn services.ai_inference_service.app:app --host 127.0.0.1 --port 8002
```

API Gateway:

```powershell
$env:AI_SERVICE_URL = "http://127.0.0.1:8002"
$env:DATABASE_SERVICE_URL = "http://127.0.0.1:8001"
python -m uvicorn services.api_gateway.main:app --host 127.0.0.1 --port 8000
```

Dashboard Service:

```powershell
$env:API_GATEWAY_URL = "http://127.0.0.1:8000"
python -m streamlit run services\dashboard_service\app.py --server.port 8501
```

Open `http://127.0.0.1:8501`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q services
```

The latest full local run completed with 30 tests passed. The remaining test
warnings are dependency deprecation notices and do not represent failed tests.

## Docker

Each microservice has its own Dockerfile and requirements file. Build all four
images from the repository root:

```powershell
docker build -t autocare-database:latest services\database_service
docker build -t autocare-dashboard:latest services\dashboard_service
docker build -t autocare-ai-inference:latest services\ai_inference_service
docker build -t api-gateway:latest -f services\api_gateway\Dockerfile .
```

Create a shared network and start the services in dependency order:

```powershell
docker network create autocare-network
docker run --rm -d --name autocare-db --network autocare-network -p 8001:8000 -e DATABASE_PATH=/data/autocare.db -v autocare-db-data:/data autocare-database:latest
docker run --rm -d --name autocare-ai --network autocare-network -p 8002:8001 autocare-ai-inference:latest
docker run --rm -d --name autocare-api --network autocare-network -p 8000:8000 -e AI_SERVICE_URL=http://autocare-ai:8001 -e DATABASE_SERVICE_URL=http://autocare-db:8000 api-gateway:latest
docker run --rm -d --name autocare-dashboard --network autocare-network -p 8501:8501 -e API_GATEWAY_URL=http://autocare-api:8000 autocare-dashboard:latest
docker ps
```

Open `http://127.0.0.1:8501`. Stop the containers after testing:

```powershell
docker stop autocare-dashboard autocare-api autocare-ai autocare-db
```

Public versioned images used by Kubernetes:

| Service | Public image |
|---|---|
| Dashboard | `caozhenyu33/autocare-dashboard:v1` |
| API Gateway | `aadgmagar/api-gateway:v1` |
| AI Inference | `ivolim/autocare-ai-inference:v1` |
| Database | `caozhenyu33/autocare-database:v1` |

## Kubernetes and Minikube

The `k8s/` directory contains a Deployment and Service for every microservice.
The Database manifest also contains a 1 Gi persistent volume claim, and the
Dashboard is exposed through a NodePort Service.

Install Minikube on Windows, start a Docker-driver cluster, and deploy in
dependency order:

```powershell
winget install Kubernetes.minikube
minikube start --driver=docker --cpus=4 --memory=6000
kubectl apply -f k8s\database.yaml
kubectl apply -f k8s\ai-inference.yaml
kubectl rollout status deployment/database --timeout=180s
kubectl rollout status deployment/ai-inference --timeout=180s
kubectl apply -f k8s\api-gateway.yaml
kubectl rollout status deployment/api-gateway --timeout=180s
kubectl apply -f k8s\dashboard.yaml
kubectl rollout status deployment/dashboard --timeout=180s
kubectl get pods,services,pvc
minikube service dashboard-service
```

The AI Inference Deployment is the scaling target. To demonstrate manual
horizontal scaling:

```powershell
kubectl scale deployment ai-inference --replicas=1
kubectl rollout status deployment/ai-inference --timeout=180s
kubectl scale deployment ai-inference --replicas=3
kubectl rollout status deployment/ai-inference --timeout=180s
kubectl get pods -l app=ai-inference
```

Database persistence can be checked by creating prediction history, restarting
the Database Deployment, and confirming the same records remain:

```powershell
kubectl rollout restart deployment/database
kubectl rollout status deployment/database --timeout=180s
kubectl get pvc
```

The complete four-service prediction, history, persistence, and three-replica
AI flow has been verified on a local Minikube cluster.

## Environment variables

| Variable | Service | Local default | Container/Kubernetes value |
|---|---|---|---|
| `API_GATEWAY_URL` | Dashboard | `http://127.0.0.1:8000` | Gateway service URL |
| `DATABASE_PATH` | Database | `services/database_service/data/autocare.db` | `/data/autocare.db` |
| `AI_SERVICE_URL` | API Gateway | `http://127.0.0.1:8002` | `http://ai-inference-service:8001` |
| `DATABASE_SERVICE_URL` | API Gateway | `http://127.0.0.1:8001` | `http://database-service:8000` |

## Known integration limitations

- Minikube is a local development cluster; this project has not been deployed to a production Kubernetes environment.
- AI scaling is manual through `kubectl scale`; no metrics-based HorizontalPodAutoscaler is configured.
- SQLite uses one Database replica and a ReadWriteOnce persistent volume. It is not designed for multiple concurrent Database replicas.
- Current dependency versions emit Pydantic and Starlette deprecation warnings during tests; these warnings do not prevent the verified application flow.
