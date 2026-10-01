FROM python:3.11-slim

WORKDIR /app

# Install system utilities needed for build/compiles
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and files
COPY app/ ./app/
COPY mlflow.db .
COPY nc_prediction.db .
COPY seed.py .

# Seed the database during container build if database is empty
RUN python seed.py

EXPOSE 80

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
