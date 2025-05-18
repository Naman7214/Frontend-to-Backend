from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
from src.app.config.database import mongodb_database
from src.app.routes.backend_code_gen_route import (
    router as backend_code_gen_router,
)
from src.app.services.langfuse_service import langfuse_service
from src.app.utils.logging_utils import loggers
from src.app.utils.tracing_context_utils import (
    request_context,
    tracer_context,
    user_query_context,
)


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    mongodb_database.connect()
    yield
    mongodb_database.disconnect()


app = FastAPI(title="My FastAPI Application", lifespan=db_lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def set_user_query_middleware(request: Request, call_next):
    # Extract user query from request
    user_query = None
    token = None

    try:
        if request.method == "POST":
            try:
                body = await request.json()
                user_query = body.get("url", None)
                loggers["lfuse"].info(f"Extracted user query: {user_query}")
            except:
                loggers["lfuse"].info("Could not parse request body as JSON")

        # Set context
        if user_query:
            token = user_query_context.set(user_query)
            loggers["lfuse"].info(f"Set user query context: {user_query}")

        response = await call_next(request)
        return response
    except Exception as e:
        loggers["lfuse"].error(f"Error in user query middleware: {str(e)}")
        return await call_next(request)
    finally:
        # Always clean up the context
        if token:
            user_query_context.reset(token)
            loggers["lfuse"].info("Reset user query context")


@app.middleware("http")
async def create_unified_trace(request: Request, call_next):
    try:
        trace_id = request.headers.get("X-Request-ID", None)
        loggers["lfuse"].info(f"Trace ID: {trace_id}")
        
        # Only create trace if we have a valid trace ID
        if trace_id and trace_id != "None" and trace_id != "":
            trace = langfuse_service.langfuse_client.trace(id=trace_id)
            request.state.trace_id = trace_id
        elif request_context.get() and request_context.get() != "None" and request_context.get() != "":
            # Use request_context if we have one and no trace_id
            trace = langfuse_service.langfuse_client.trace(
                id=request_context.get(),
                name=f"Trace ID {request_context.get()}",
            )
            token = tracer_context.set(trace)
            loggers["lfuse"].info(f"trace object created for trace_id: {trace.id}")
            loggers["lfuse"].info(f"trace object: {trace}")
            trace_id = trace.id
            loggers["lfuse"].info(f"Created Trace ID: {trace_id}")
            request.state.trace_id = trace_id
        else:
            # No valid trace IDs available, skip trace creation
            request.state.trace_id = None
            
        response = await call_next(request)

        # Only add header if we have a valid trace ID
        if request.state.trace_id:
            response.headers["X-Trace-ID"] = request.state.trace_id
    finally:
        if 'token' in locals():
            tracer_context.reset(token)

    return response


@app.middleware("http")
async def set_request_context(request: Request, call_next):
    token = None
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    loggers["lfuse"].info(f"request object: {request}")
    loggers["lfuse"].info("inside set_request_context")
    loggers["lfuse"].info(f"Request ID: {request_id}")
    if request_context.get() is None:
        token = request_context.set(request_id)
        loggers["lfuse"].info(f"Token: {token}")
    try:
        response = await call_next(request)
    finally:
        if token is not None:
            request_context.reset(token)
        loggers["lfuse"].info(f"Request ID: {request_context.get()}")

    response.headers["X-Request-ID"] = request_id
    return response


# Add middleware in the correct order
app.middleware("http")(set_request_context)
app.middleware("http")(set_user_query_middleware)
app.middleware("http")(create_unified_trace)


@app.get("/")
async def root():
    return {"message": "Welcome to my FastAPI application!"}


# Include routers
app.include_router(backend_code_gen_router, tags=["Backend Code Generator"])
