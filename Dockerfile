FROM python:3.9-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create required directories
RUN mkdir -p data/exports templates/email blockchain/abi

# Initialize database
RUN python setup/db_init.py

# Environment variables
ENV PYTHONPATH=/app

# Set default command
CMD ["python", "slack_integration/main_app_update.py"] 