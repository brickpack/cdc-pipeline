FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p /var/log/api-ingestion && \
    chmod 777 /var/log/api-ingestion

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the ingestion service
CMD ["python", "linkedin_ingestion.py"]
