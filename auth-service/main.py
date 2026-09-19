from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="auth-service")
Instrumentator().instrument(app).expose(app)  # exposes /metrics

# Hardcoded allow-list — this is a mock validator, not real auth.
VALID_TOKENS = {"demo-token-123", "demo-token-456"}


class TokenRequest(BaseModel):
    token: str


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/validate")
def validate(req: TokenRequest):
    return {"valid": req.token in VALID_TOKENS}
