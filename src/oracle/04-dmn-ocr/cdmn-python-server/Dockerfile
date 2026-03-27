ARG BASE_IMAGE=python:3.9-slim
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY cdmn.py .
# .env is optional; prefer runtime env vars or bind-mount if needed

EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
