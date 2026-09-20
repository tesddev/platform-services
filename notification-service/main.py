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


import logging
from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

app = FastAPI(title="notification-service")
Instrumentator().instrument(app).expose(app)


class NotifyRequest(BaseModel):
    email: str
    message: str


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/notify")
def notify(req: NotifyRequest):
    # Real implementation would call an email provider here.
    logger.info(f"Notification queued for {req.email}: {req.message}")
    return {"status": "queued"}
