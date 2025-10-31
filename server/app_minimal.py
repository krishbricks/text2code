"""Minimal test FastAPI app."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App starting up...")
    yield
    print("App shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/health')
async def health():
    return {'status': 'healthy', 'version': '0.1.0'}

@app.get('/api/health')
async def api_health():
    return {'status': 'api healthy'}

print("✅ Minimal app loaded successfully")
