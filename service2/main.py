import os
import uuid
from fastapi import FastAPI, Request
from common.logging import get_logger, configure_logging, REQUEST_ID

configure_logging()
app = FastAPI()


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID")
    request.state.request_id = req_id
    request.state.logger = get_logger('service2', request_id=req_id)
    token = REQUEST_ID.set(req_id)
    try:
        request.state.logger.info("request.start")
        response = await call_next(request)
    finally:
        REQUEST_ID.reset(token)
    response.headers["X-Request-ID"] = req_id
    return response


@app.post("/process")
async def process(request: Request):
    payload = await request.json()
    logger = request.state.logger
    logger.info("process.received", extra={"payload": payload})
    # do minimal processing and echo
    result = {"echo": payload}
    logger.info("process.complete", extra={"result": result})
    return {"status": "processed", "result": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service2.main:app", host="0.0.0.0", port=8001, log_level="info")
