# AutoCare AI Dashboard and Database Design

## Goal

Implement the Dashboard Service and Database Service owned by this team member while preserving the existing four-service architecture and the API/AI teammates' ownership boundaries.

## Authoritative contracts

- Dashboard sends vehicle telemetry only to `POST {API_GATEWAY_URL}/predict`.
- Dashboard retrieves history only from `GET {API_GATEWAY_URL}/history`.
- Database exposes `GET /health`, `POST /records`, `GET /records`, and `GET /records/{record_id}`.
- Telemetry field names and validation limits exactly match `services/api_gateway/schemas.py` and `services/ai_inference_service/app.py`.
- Prediction values are stored and displayed without remapping.
- The authoritative model classes are `Safe for Driving`, `At Risk`, and `Needs Immediate Maintenance`.
- The model and `test_data.xlsx` are not modified or retrained.
- The API Gateway and AI Inference Service source files are not modified.

## Dashboard Service

The Streamlit application presents the ten telemetry inputs using the API schema's numeric limits. On submission it sends the exact JSON field names to the configured API Gateway and displays the API response without generating or substituting a prediction.

Display styling is selected from the actual returned value:

- `Safe for Driving`: success presentation.
- `At Risk`: warning presentation.
- `Needs Immediate Maintenance`: error presentation.
- Any other value: neutral informational presentation while preserving the returned text.

The API client uses a finite timeout and converts connection, timeout, HTTP, JSON, and schema problems into readable UI messages. History accepts either a JSON array or a `{ "records": [...] }` wrapper to tolerate the API teammate's eventual response design. A missing `/history` endpoint is shown as a clear pending-integration message. The dashboard never accesses SQLite or the AI service directly.

## Database Service

The database service uses FastAPI, Pydantic, the Python `sqlite3` module, and a file path selected through `DATABASE_PATH`. Its local default is a service-local `data/autocare.db`; containers and Kubernetes set `/data/autocare.db`.

The service creates its parent directory and table automatically. Each record contains an integer ID, UTC timestamp, validated telemetry JSON, `maintenance_decision`, `confidence_score`, identified issues, and optional recommendation/model version. `maintenance_decision` is an unrestricted non-empty string and is stored exactly as submitted.

SQLite access uses short-lived connections and parameterized statements. Stored JSON is decoded back to typed response data. Missing records return HTTP 404; storage failures return HTTP 500 without exposing internal database details.

## Container and Kubernetes design

Each owned service has an independent requirements file and Dockerfile. The database image listens on port 8000 and stores data under `/data`. The dashboard image listens on `0.0.0.0:8501` and reads `API_GATEWAY_URL`.

Kubernetes adds:

- Database PersistentVolumeClaim, one-replica Deployment, ClusterIP Service, `/data` mount, and `/health` probes.
- Dashboard one-replica Deployment, NodePort Service, `API_GATEWAY_URL=http://api-gateway-service:8000`, and Streamlit health probes.

No Docker Compose file is created because the API Gateway and AI Inference services do not yet have Dockerfiles. No API/AI Kubernetes manifests are created on their owners' behalf.

## Documentation

The README is expanded with current class names, service responsibilities, local and container commands, Kubernetes instructions for the owned services, dataset information, and honest known limitations. The existing architecture explanation replaces only the obsolete planned class names; service topology is unchanged.

## Testing and verification

Tests are written before production code:

- Database tests use a temporary SQLite path and prove health, create/list/get behavior, exact prediction-value preservation, validation, and 404 behavior.
- Dashboard tests exercise payload construction, class-to-display mapping, prediction responses, history formats, and network/error handling without launching external services.
- The Streamlit process is started and its health endpoint is probed.
- Docker builds and container smoke tests are attempted only if the Docker daemon is available.
- Kubernetes YAML is parsed with kubectl when available. Minikube deployment is not claimed because Minikube is absent.

## Ownership and delivery constraints

- Do not edit the API Gateway or AI Inference Service code.
- Do not create fake predictions or bypass the API Gateway.
- Do not alter or retrain the model or dataset.
- Do not delete teammates' work.
- Do not commit or push.
