# ---- builder ----
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- runtime ----
FROM python:3.12-slim
LABEL maintainer="tesddev"
LABEL description="Minimal service for the capstone microservices platform"
RUN adduser --disabled-password --gecos '' appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY main.py .
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
