from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.app.config.database import mongodb_database
from src.app.routes.backend_code_gen_route import router as backend_code_gen_router


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    mongodb_database.connect()
    yield
    mongodb_database.disconnect()


app = FastAPI(title="My FastAPI Application", lifespan=db_lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to my FastAPI application!"}

# Include routers
app.include_router(backend_code_gen_router, tags=["Backend Code Generator"])