from contextvars import ContextVar

from fastapi import Request
from langfuse.client import StatefulTraceClient

# Create a context variable to store the request
request_context: ContextVar[Request] = ContextVar(
    "request_context", default=None
)
tracer_context: ContextVar[StatefulTraceClient] = ContextVar(
    "tracer_context", default=None
)