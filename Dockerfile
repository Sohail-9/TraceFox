# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage 
FROM python:3.11-slim AS runtime

# Create application user
RUN addgroup --system app && adduser --system --group app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:${PATH}"

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder --chown=app:app /root/.local /home/app/.local
COPY --chown=app:app services ./services
COPY --chown=app:app scripts ./scripts

USER app

ENV TRACEFOX_ENVIRONMENT=production

EXPOSE 8000

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
