import uvicorn
from fastapi import FastAPI

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
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

# Tracing setup (Console exporter for demo)
provider = TracerProvider()
processor = SimpleSpanProcessor(make_exporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="otel-service2")
FastAPIInstrumentor().instrument_app(app)


@app.post("/work")
async def do_work(payload: dict):
    with tracer.start_as_current_span("service2.work"):
        # minimal processing
        return {"status": "processed", "received": payload}


if __name__ == "__main__":
    uvicorn.run("otel_service2.main:app", host="0.0.0.0", port=9001, log_level="info")
