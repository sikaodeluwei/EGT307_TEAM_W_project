# AutoCare AI Dashboard and Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the team member's tested Dashboard and Database microservices with Docker/Kubernetes packaging and documentation consistent with the trained model's actual class labels.

**Architecture:** Streamlit communicates only with the API Gateway through a small HTTP client module. FastAPI exposes an independent SQLite record service using exact telemetry fields and JSON persistence. Deployment configuration connects services by environment variables without changing teammate-owned code.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, SQLite, Streamlit, Requests, Pytest, Docker, Kubernetes YAML.

## Global Constraints

- Authoritative classes: `Safe for Driving`, `At Risk`, `Needs Immediate Maintenance`.
- Preserve `maintenance_decision` exactly; never remap or generate a prediction.
- Do not modify `services/api_gateway`, `services/ai_inference_service`, `test_data.xlsx`, or the trained model.
- Do not create Docker Compose until all four service Dockerfiles exist.
- Do not claim Minikube deployment because Minikube is unavailable.
- Do not commit or push.

---

### Task 1: Database behavior tests

**Files:**
- Create: `services/database_service/tests/test_app.py`

**Interfaces:**
- Consumes: `DATABASE_PATH` environment variable.
- Produces: executable requirements for `app`, `initialize_database()`, `/health`, `/records`, and `/records/{record_id}`.

- [ ] **Step 1: Write failing endpoint tests**

Create a temporary database fixture, post a complete telemetry record whose decision is `Unexpected Future Label`, and assert the same value is returned by create/list/get. Add invalid-payload and missing-ID assertions.

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m pytest services/database_service/tests/test_app.py -v`

Expected: collection fails because `services.database_service.app` does not exist.

### Task 2: Database service implementation

**Files:**
- Create: `services/database_service/app.py`
- Create: `services/database_service/requirements.txt`
- Create: `services/database_service/Dockerfile`
- Delete: `services/database_service/.placeholder2`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `DATABASE_PATH`, defaulting to `services/database_service/data/autocare.db`.
- Produces: `GET /health`, `POST /records`, `GET /records`, `GET /records/{record_id}`.

- [ ] **Step 1: Define exact telemetry and record models**

Use the ten field names and bounds from `services/api_gateway/schemas.py`. Define `PredictionRecordCreate` with `maintenance_decision: str = Field(min_length=1)`, confidence, issues, and optional recommendation/model version.

- [ ] **Step 2: Implement SQLite initialization and parameterized CRUD**

Create a `prediction_records` table with JSON text columns for input and issues. Generate UTC timestamps server-side and preserve decision text verbatim.

- [ ] **Step 3: Implement FastAPI endpoints and safe errors**

Return typed records, newest-first lists, 404 for missing IDs, and a health result that confirms the database can execute `SELECT 1`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `python -m pytest services/database_service/tests/test_app.py -v`

Expected: all database tests pass.

### Task 3: Dashboard HTTP-client tests

**Files:**
- Create: `services/dashboard_service/tests/test_api_client.py`

**Interfaces:**
- Consumes: a Requests-compatible session and API Gateway base URL.
- Produces: requirements for `predict_vehicle`, `fetch_history`, `get_display_level`, `ApiClientError`, and `HistoryUnavailableError`.

- [ ] **Step 1: Write failing prediction tests**

Assert the exact telemetry payload is sent to `/predict`, the API decision is unchanged, all three actual labels map to `success`/`warning`/`error`, and unknown labels map to `info`.

- [ ] **Step 2: Write failing history and error tests**

Assert history accepts a list and `{ "records": [...] }`, a 404 raises `HistoryUnavailableError`, and timeout/connection/HTTP/invalid JSON/invalid response cases raise `ApiClientError`.

- [ ] **Step 3: Run tests and confirm RED**

Run: `python -m pytest services/dashboard_service/tests/test_api_client.py -v`

Expected: collection fails because `services.dashboard_service.api_client` does not exist.

### Task 4: Dashboard implementation

**Files:**
- Create: `services/dashboard_service/api_client.py`
- Create: `services/dashboard_service/app.py`
- Create: `services/dashboard_service/requirements.txt`
- Create: `services/dashboard_service/Dockerfile`
- Delete: `services/dashboard_service/.placeholder`

**Interfaces:**
- Consumes: `API_GATEWAY_URL`, default `http://127.0.0.1:8000`.
- Produces: Streamlit vehicle form, prediction presentation, and history table.

- [ ] **Step 1: Implement the tested API client**

Normalize only the base URL, use a 10-second timeout, call `/predict` and `/history`, validate response shapes, and never replace API values.

- [ ] **Step 2: Run client tests and confirm GREEN**

Run: `python -m pytest services/dashboard_service/tests/test_api_client.py -v`

Expected: all client tests pass.

- [ ] **Step 3: Implement the Streamlit UI**

Use the exact field names in the submitted dictionary, schema bounds in widgets, class-specific Streamlit status functions, and a history refresh action that displays errors without crashing.

- [ ] **Step 4: Compile and start Streamlit**

Run: `python -m compileall -q services/dashboard_service` and start `streamlit run services/dashboard_service/app.py --server.headless true --server.port 8501`; probe `http://127.0.0.1:8501/_stcore/health`.

Expected: compilation succeeds and health returns HTTP 200.

### Task 5: Kubernetes configuration

**Files:**
- Create: `k8s/database.yaml`
- Create: `k8s/dashboard.yaml`

**Interfaces:**
- Consumes: images `autocare-database:latest`, `autocare-dashboard:latest`; service name `api-gateway-service`.
- Produces: PVC-backed internal database and externally reachable dashboard.

- [ ] **Step 1: Add database resources**

Create a 1 Gi ReadWriteOnce PVC, one-replica Deployment with `/data` mount and `DATABASE_PATH=/data/autocare.db`, ClusterIP `database-service`, and `/health` probes.

- [ ] **Step 2: Add dashboard resources**

Create a one-replica Deployment with `API_GATEWAY_URL=http://api-gateway-service:8000`, `/_stcore/health` probes, and NodePort `dashboard-service` on port 8501.

- [ ] **Step 3: Parse manifests**

Run: `kubectl apply --dry-run=client --validate=false -f k8s/database.yaml` and the same for `k8s/dashboard.yaml`.

Expected: both files are accepted by the client-side parser. Do not claim cluster deployment.

### Task 6: Documentation consistency

**Files:**
- Modify: `README.md`
- Modify: `system architect/system_architect_explaination`

**Interfaces:**
- Consumes: actual code, environment variables, endpoint paths, and assessment guide requirements.
- Produces: build/run/deploy documentation and current prediction names.

- [ ] **Step 1: Replace obsolete planned prediction labels**

Replace every obsolete planned prediction label with the authoritative labels in the approved design. Preserve the architecture topology.

- [ ] **Step 2: Expand README**

Document all four services, dataset/model labels, local commands, Docker commands for owned services, Kubernetes commands, known integration gaps, and Minikube limitation.

- [ ] **Step 3: Scan for stale labels**

Run a repository text scan excluding `.git`, the source dataset/model, and planning evidence. Expected: no obsolete prediction-class references remain in README, architecture documentation, or owned implementation.

### Task 7: Fresh verification and handoff

**Files:**
- Verify all created and modified files.

**Interfaces:**
- Consumes: completed implementation.
- Produces: evidence-backed final report without a commit.

- [ ] **Step 1: Run all automated tests and compilation**

Run both pytest suites and `python -m compileall -q services`.

- [ ] **Step 2: Run database live HTTP smoke test**

Start Uvicorn on a temporary port/path, call health, POST, list, and get, then stop it.

- [ ] **Step 3: Run Streamlit smoke test**

Start headless Streamlit, probe its health endpoint, then stop it.

- [ ] **Step 4: Attempt Docker verification when daemon is available**

Build both images and smoke-test both containers. If the daemon is unavailable, report the exact failure and do not claim builds.

- [ ] **Step 5: Recheck ownership and repository status**

Run `git diff -- services/api_gateway services/ai_inference_service test_data.xlsx`, class-name scans, `git diff --check`, and `git status --short`.

- [ ] **Step 6: Report exact evidence and next commands**

List created/modified files, tests and results, class references changed, API teammate requirements, commands to run, and the unchanged ownership boundaries.
