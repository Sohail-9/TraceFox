FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY services ./services
COPY scripts ./scripts

ENV KRUTRIM_MODEL=Krutrim-DeepSeek-R1 \
    KRUTRIM_API_BASE_URL=https://api.krutrim.com/v1 \
    DEEPSEEK_ROUTER_MODEL=deepseek-r1

EXPOSE 8000

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

