"""Code generation API router with multi-step workflow support."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List

from server.services.pyspark_generator import generate_pyspark_code, get_databricks_token

router = APIRouter()


class Step(BaseModel):
    """Progress step model."""
    name: str
    status: str  # 'pending', 'in_progress', 'completed', 'error'
    message: Optional[str] = None


class GenerateRequest(BaseModel):
    """Request model for code generation."""
    source_type: str = Field(..., description="'volume' or 'jira'")
    input_volume_path: Optional[str] = Field(None, description="Path to mapping CSV in UC Volume (optional if mapping_csv_content provided)")
    output_volume_path: str = Field(..., description="Path where generated code will be saved")
    pattern: str = Field(default="pyspark", description="ETL pattern (only 'pyspark' supported)")
    mapping_csv_content: Optional[str] = Field(None, description="CSV content as string (optional - provide this OR input_volume_path)")


class GenerateResponse(BaseModel):
    """Response model for code generation."""
    code: str = Field(..., description="Generated PySpark code")
    steps: List[Step] = Field(..., description="Progress steps")
    success: bool


@router.post("/generate-pyspark", response_model=GenerateResponse)
async def generate_pyspark_endpoint(
    body: GenerateRequest,
    request: Request
):
    """Generate PySpark code from mapping CSV with step tracking."""

    steps: List[Step] = []

    # Extract token from request headers (Databricks Apps injects this automatically)
    auth_header = request.headers.get("Authorization", "")
    request_token = None
    if auth_header.startswith("Bearer "):
        request_token = auth_header.replace("Bearer ", "")

    # Also check for Databricks-specific headers
    if not request_token:
        request_token = request.headers.get("X-Databricks-Token")

    # Step 1: Validate input
    steps.append(Step(name="Validating input", status="in_progress"))

    if body.source_type == "jira":
        steps[-1].status = "error"
        steps[-1].message = "JIRA integration is work in progress"
        raise HTTPException(
            status_code=501,
            detail="JIRA integration is not yet implemented. Please use 'volume' source type."
        )

    if not body.input_volume_path:
        steps[-1].status = "error"
        steps[-1].message = "Input volume path is required"
        raise HTTPException(status_code=400, detail="input_volume_path is required")

    if not body.output_volume_path:
        steps[-1].status = "error"
        steps[-1].message = "Output volume path is required"
        raise HTTPException(status_code=400, detail="output_volume_path is required")

    if body.pattern != "pyspark":
        steps[-1].status = "error"
        steps[-1].message = "Only 'pyspark' pattern is currently supported"
        raise HTTPException(status_code=400, detail="Only 'pyspark' pattern is supported")

    steps[-1].status = "completed"
    steps[-1].message = "Input validated successfully"

    # Step 2: Prepare input (CSV content or volume path)
    steps.append(Step(name="Preparing input", status="in_progress"))

    try:
        if body.mapping_csv_content:
            print(f"DEBUG: Using CSV content provided directly in request ({len(body.mapping_csv_content)} bytes)")
            steps[-1].status = "completed"
            steps[-1].message = f"✓ Using CSV content from request"
        elif body.input_volume_path:
            print(f"DEBUG: Will read CSV from volume path: {body.input_volume_path}")
            steps[-1].status = "completed"
            steps[-1].message = f"✓ Input volume path: {body.input_volume_path}"
        else:
            raise HTTPException(
                status_code=400,
                detail="Either mapping_csv_content or input_volume_path must be provided"
            )

    except HTTPException:
        raise
    except Exception as e:
        steps[-1].status = "error"
        steps[-1].message = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to prepare input: {str(e)}")

    # Step 3: Generate code structure (reading CSV handled internally)
    steps.append(Step(name="Generating code structure", status="in_progress"))

    try:
        # Call code generation with appropriate parameters
        # The generate_pyspark_code function handles both CSV content and volume path reading
        code = generate_pyspark_code(
            mapping_csv_content=body.mapping_csv_content,
            input_volume_path=body.input_volume_path,
            request_token=request_token
        )

        steps[-1].status = "completed"
        steps[-1].message = "✓ Code generated successfully"
    except Exception as e:
        steps[-1].status = "error"
        steps[-1].message = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to generate code: {str(e)}")

    return GenerateResponse(
        code=code,
        steps=steps,
        success=True
    )
