import os
import time
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
resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "auth-service")})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "tempo.monitoring.svc.cluster.local:4317"),
    insecure=True,
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

app = FastAPI(title="auth-service")
app.add_middleware(PrometheusMiddleware)
FastAPIInstrumentor.instrument_app(app)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- Routes ---
class TokenRequest(BaseModel):
    token: str

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/validate")
async def validate_token(req: TokenRequest):
    if req.token == "demo-token-123":
        return {"valid": True}
    raise HTTPException(status_code=401, detail="Invalid token")
