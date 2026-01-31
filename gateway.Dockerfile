FROM python:3.11-slim

WORKDIR /app

# Copy requirements files
COPY requirements.txt gateway_requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r gateway_requirements.txt

# Copy application files
COPY auth_models.py ./
COPY services/user_auth_service.py ./services/
COPY gateway/ ./gateway/
COPY infrastructure/ ./infrastructure/

# Expose gateway port
EXPOSE 8001

# Run gateway service
CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8001"]
