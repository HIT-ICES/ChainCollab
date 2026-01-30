FROM python:3.9-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY cdmn.py .
COPY .env .

EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
