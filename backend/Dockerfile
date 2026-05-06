FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl gcc libpq-dev spamc clamdscan \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source into /app/backend/ so "from backend.xxx import" works
COPY . ./backend/

# Create a minimal top-level entry so uvicorn can find backend.main:app
ENV PYTHONPATH=/app

EXPOSE 25 587 993 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
