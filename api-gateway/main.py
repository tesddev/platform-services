import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "unknown-service")})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "tempo.monitoring.svc.cluster.local:4317"),
    insecure=True,
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

HTTPXClientInstrumentor().instrument()


import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="api-gateway")
Instrumentator().instrument(app).expose(app)

# Injected via ConfigMap once this is on the cluster — defaults are for local runs.
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
