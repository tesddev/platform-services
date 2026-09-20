import os
import time
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# --- Prometheus Middleware ---
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency",
    ["method", "path"]
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(time.time() - start)
        return response

# --- OpenTelemetry Setup ---
resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "api-gateway")})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "tempo.monitoring.svc.cluster.local:4317"),
    insecure=True,
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
HTTPXClientInstrumentor().instrument()

app = FastAPI(title="api-gateway")
app.add_middleware(PrometheusMiddleware)
FastAPIInstrumentor.instrument_app(app)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- Routes ---
AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
NOTIFY_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8002")

class TokenRequest(BaseModel):
    token: str

class NotifyRequest(BaseModel):
    email: str
    message: str

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/route/auth")
async def route_auth(req: TokenRequest):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.post(f"{AUTH_URL}/validate", json=req.model_dump())
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"auth-service unreachable: {e}")

@app.post("/route/notify")
async def route_notify(req: NotifyRequest):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.post(f"{NOTIFY_URL}/notify", json=req.model_dump())
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"notification-service unreachable: {e}")
