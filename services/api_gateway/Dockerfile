FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY services/api_gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API Gateway code and dependencies
COPY services/api_gateway /app/services/api_gateway

ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
