Design and logging details
=========================

Overview
--------

This small workspace provides two FastAPI services (`service1` and `service2`) and a shared logging helper (`common/logging.py`). The key goal is to propagate a request identifier (`X-Request-ID`) through the call chain and to produce structured JSON logs that include the same request id for all log messages, including those emitted by third-party libraries such as `httpx`.

High-level flow
---------------

- Client -> `service1` POST /proxy
- `service1` middleware: read `X-Request-ID` header if present; otherwise generate a UUID. Set `request.state.request_id` and attach a per-request `LoggerAdapter`. Also set the global `REQUEST_ID` ContextVar for the lifetime of the request.
- `service1` forwards the request to `service2`, including the `X-Request-ID` header.
- `service2` middleware: read `X-Request-ID` header if present; otherwise generate a UUID. Set `request.state.request_id`, attach a per-request `LoggerAdapter`, and set the `REQUEST_ID` ContextVar for the request.

Why we added a ContextVar
-------------------------

LoggerAdapter vs global injection

- `logging.LoggerAdapter` injects extra context into records emitted through that adapter only. That means any code that uses `logger = get_logger(...)` will have the `request_id` attached when it logs.
- However, many libraries (for example `httpx`, `uvicorn`, or other frameworks) use their own loggers and don't use our `LoggerAdapter`. Records those libraries emit don't have our adapter's `extra` fields, so the `request_id` is missing.

ContextVar + logging.Filter solves this

- A `ContextVar` (here named `REQUEST_ID`) allows storing context that is local to the current asynchronous task context. In async frameworks (FastAPI/Starlette), each incoming request runs in its own task context; `ContextVar` values are preserved across `await` boundaries for that task.
- We add a `RequestIdFilter` to the root handler. The filter runs for every `LogRecord` and sets `record.request_id` from the `REQUEST_ID` ContextVar. Because the filter is applied at the handler level, every logger that emits to that handler (including third-party library loggers) will have `request_id` set on its `LogRecord` before formatting.

Why ContextVar and not thread-local or global
--------------------------------------------

- Thread-local storage (`threading.local`) is not sufficient in async programs because many requests share the same thread and switch tasks; thread-local will not carry per-request state across awaits.
- A global variable is obviously unsafe because concurrent requests would overwrite it.
- `ContextVar` is designed for async task-local context: values are preserved per logical execution context and can be safely set/reset in middleware.

How the middleware uses ContextVar safely
----------------------------------------

- In each middleware we call `token = REQUEST_ID.set(req_id)` before calling downstream handlers. This sets the ContextVar for the current context and returns a token.
- In a `finally` block we call `REQUEST_ID.reset(token)` to restore the previous value. Reset is important when nested contexts or background tasks are used, to avoid leaking values.

Concurrency and background tasks
--------------------------------

- The `REQUEST_ID` ContextVar value is attached to the logical execution context. If you schedule background work that should inherit the request id, ensure that the background task is created while the ContextVar is set; otherwise, explicitly pass the ID into the background task.

What you get
------------

- Every JSON log line emitted by the service, or by libraries the service uses, will include `request_id` (or `null` when no request context is present). This greatly simplifies tracing logs from multiple services and makes it straightforward to correlate logs across service boundaries.

Notes and caveats
-----------------

- The JSON formatter expects `record.request_id` to exist; the `RequestIdFilter` ensures the attribute is present (it sets `None` when no id is available).
- If you spawn threads or external workers, ContextVar does not automatically cross thread boundaries; pass the ID explicitly if needed.
- For more advanced structured logging features (e.g., faster context propagation, richer event model), consider `structlog` or similar libraries. The current approach is intentionally small and dependency-light.

How to verify
-------------

1. Start both services:

```bash
uvicorn service2.main:app --port 8001
uvicorn service1.main:app --port 8000
```

2. Send a request to `service1`:

```bash
curl -v -X POST http://localhost:8000/proxy -H 'Content-Type: application/json' -d '{"name":"Alice"}'
```

3. Inspect the stdout of both services. You should see JSON log lines similar to:

```
{"asctime": "...", "levelname": "INFO", "name": "service1", "message": "proxy.received", "request_id": "<uuid>"}
{"asctime": "...", "levelname": "INFO", "name": "httpx", "message": "HTTP Request: POST ...", "request_id": "<same-uuid>"}
{"asctime": "...", "levelname": "INFO", "name": "service2", "message": "process.received", "request_id": "<same-uuid>"}
```

Summary
-------

Using a `ContextVar` for `request_id` plus a logging `Filter` gives per-request, async-safe propagation of contextual data to all loggers, including third-party library loggers. This produces consistent, structured JSON logs that contain `request_id` for easier tracing and debugging across service boundaries.
