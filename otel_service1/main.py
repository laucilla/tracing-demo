"""Service 1 with OpenTelemetry instrumentation.

This service demonstrates distributed tracing using OpenTelemetry with support for multiple
exporters (console, OTLP, Jaeger). It automatically instruments FastAPI and HTTP client calls
for comprehensive tracing across the service mesh.
"""
import os
import uvicorn
from fastapi import FastAPI
import httpx

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
import os

# optional exporters
OTEL_EXPORTER = os.getenv("OTEL_EXPORTER", "console").lower()
if OTEL_EXPORTER == "otlp":
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        def make_exporter():
            endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            if endpoint:
                return OTLPSpanExporter(endpoint=endpoint)
            return OTLPSpanExporter()
    except Exception:
        make_exporter = lambda: ConsoleSpanExporter()
elif OTEL_EXPORTER == "jaeger":
    try:
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter

        def make_exporter():
            agent_host = os.getenv("OTEL_EXPORTER_JAEGER_AGENT_HOST")
            agent_port = int(os.getenv("OTEL_EXPORTER_JAEGER_AGENT_PORT", "6831"))
            return JaegerExporter(agent_host_name=agent_host, agent_port=agent_port)
    except Exception:
        make_exporter = lambda: ConsoleSpanExporter()
else:
    make_exporter = lambda: ConsoleSpanExporter()
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Tracing setup (Console exporter for demo)
provider = TracerProvider()
processor = SimpleSpanProcessor(make_exporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="otel-service1")
FastAPIInstrumentor().instrument_app(app)
HTTPXClientInstrumentor().instrument()

SERVICE2_URL = os.getenv("OTEL_SERVICE2_URL", "http://otel_service2:9001/work")


@app.post("/call")
async def call_service(payload: dict):
    """Endpoint that calls Service 2 with OpenTelemetry tracing.
    
    Accepts a JSON payload, creates a span for the service call, and forwards 
    the request to Service 2, returning the downstream response wrapped with status confirmation.
    """
    with tracer.start_as_current_span("service1.call"):
        async with httpx.AsyncClient() as client:
            resp = await client.post(SERVICE2_URL, json=payload, timeout=10.0)
            return {"status": "ok", "downstream": resp.json()}


if __name__ == "__main__":
    uvicorn.run("otel_service1.main:app", host="0.0.0.0", port=9000, log_level="info")
