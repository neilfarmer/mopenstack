FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

# Copy application code
COPY . .

# Install the package
RUN pip install -e .

# Expose ports for all OpenStack services
EXPOSE 5000 8774 9696 9292 8776 8080 9876 9001

# Run the application
CMD ["uvicorn", "mopenstack.main:app", "--host", "0.0.0.0", "--port", "5000"]