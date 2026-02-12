import logging
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar


# ContextVar to hold the current request id for the executing context
REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = REQUEST_ID.get()
        return True


def configure_logging():
    """Configure root logger to output JSON to stdout."""
    root = logging.getLogger()
    # avoid adding multiple handlers when re-importing
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    fmt = '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s'
    formatter = jsonlogger.JsonFormatter(fmt)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_logger(name: str = 'app', request_id: str | None = None) -> logging.LoggerAdapter:
    """Return a LoggerAdapter that injects `request_id` into log records."""
    configure_logging()
    base = logging.getLogger(name)
    extra = {'request_id': request_id}
    return logging.LoggerAdapter(base, extra)
