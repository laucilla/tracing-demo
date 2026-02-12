"""Service 1 - FastAPI application that handles HTTP requests and proxies them to Service 2.

This service acts as a proxy, receiving requests, adding request tracing headers,
and forwarding them to Service 2 with structured logging.
"""
import os
import uuid
from fastapi import FastAPI, Request
import httpx
from common.logging import get_logger, configure_logging, REQUEST_ID

configure_logging()
app = FastAPI()
SERVICE2_URL = os.getenv("SERVICE2_URL", "http://localhost:8001/process")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Middleware to inject request ID and logger into each request.
    
    Generates a unique request ID for tracing, attaches a logger to the request state,
    and sets the request ID in response headers for correlation across services.
    """
    req_id = str(uuid.uuid4())
    request.state.request_id = req_id
    request.state.logger = get_logger('service1', request_id=req_id)
    token = REQUEST_ID.set(req_id)
    try:
        request.state.logger.info("request.start")
        response = await call_next(request)
    finally:
        REQUEST_ID.reset(token)
    response.headers["X-Request-ID"] = req_id
    return response


@app.post("/proxy")
async def proxy(request: Request):
    """Proxy endpoint that forwards requests to Service 2.
    
    Extracts the request payload, logs it, forwards to Service 2 with request ID header,
    and returns the downstream response along with status confirmation.
    """
    payload = await request.json()
    logger = request.state.logger
    logger.info("proxy.received", extra={"payload": payload})
    headers = {"X-Request-ID": request.state.request_id}
    async with httpx.AsyncClient() as client:
        resp = await client.post(SERVICE2_URL, json=payload, headers=headers, timeout=10.0)
    # safe to call .json() because downstream returns json
    downstream = resp.json()
    logger.info("proxy.downstream_response", extra={"status_code": resp.status_code, "downstream": downstream})
    return {"status": "ok", "downstream": downstream}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service1.main:app", host="0.0.0.0", port=8000, log_level="info")
