# Generic router module for the Databricks app template
# Add your FastAPI routes here

from fastapi import APIRouter

router = APIRouter()

# Lazy load routers to prevent import-time failures
def _load_routers():
    try:
        from .user import router as user_router
        router.include_router(user_router, prefix='/user', tags=['user'])
    except Exception as e:
        print(f"Warning: Could not load user router: {e}")

    try:
        from .generate import router as generate_router
        router.include_router(generate_router, prefix='/code', tags=['code-generation'])
    except Exception as e:
        print(f"Warning: Could not load generate router: {e}")

    try:
        from .codegen import router as codegen_router
        router.include_router(codegen_router, prefix='/codegen', tags=['pyspark-generation'])
    except Exception as e:
        print(f"Warning: Could not load codegen router: {e}")

# Load routers when module is imported
_load_routers()
