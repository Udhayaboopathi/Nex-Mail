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

# Set PYTHONPATH so "from backend.xxx import" works from anywhere in the container
# Set ALEMBIC_CONFIG so "alembic upgrade head" works without cd
ENV PYTHONPATH=/app \
    ALEMBIC_CONFIG=/app/backend/alembic.ini

EXPOSE 25 587 993 8000

# Write startup script that runs migrations then starts uvicorn
RUN printf '#!/bin/sh\nset -e\necho "Running database migrations..."\nalembic -c /app/backend/alembic.ini upgrade head\necho "Starting uvicorn..."\nexec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1\n' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
