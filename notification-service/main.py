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
