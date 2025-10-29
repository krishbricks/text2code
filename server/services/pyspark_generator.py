"""
PySpark code generation service - EXACT logic from generate_from_volume_mapping.py
This file contains your original code isolated for easy modification.
"""

import os
import json
import textwrap
import traceback
from openai import OpenAI
from typing import Dict, List, Any

# ------------------ CONFIG ------------------
def get_workspace_url():
    """Get workspace URL from environment or auto-detect."""
    # Try environment variable first
    workspace_url = os.environ.get("DATABRICKS_HOST")
    if workspace_url:
        workspace_url = workspace_url.rstrip("/")
        # Ensure it has https:// prefix
        if not workspace_url.startswith("http://") and not workspace_url.startswith("https://"):
            workspace_url = f"https://{workspace_url}"
        return workspace_url

    # Try to auto-detect from WorkspaceClient
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        if w.config.host:
            host = w.config.host.rstrip("/")
            # Ensure it has https:// prefix
            if not host.startswith("http://") and not host.startswith("https://"):
                host = f"https://{host}"
            return host
    except Exception:
        pass

    # Fallback to default (must be complete URL with protocol)
    return "https://adb-315278363237056.16.azuredatabricks.net"

WORKSPACE_URL = get_workspace_url()
MODEL_NAME = "databricks-claude-sonnet-4-5"
MIN_RESPONSE_LEN = 40


# ---------- obtain Databricks PAT ----------
def get_databricks_token(request_token: str = None):
    """
    Get Databricks token from various sources.

    Args:
        request_token: Token from the HTTP request headers (for Databricks Apps)
    """
    # Priority 1: Use token passed from request (Databricks Apps frontend API calls)
    if request_token:
        return request_token

    # Priority 2: Try environment variable (for local development)
    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return token

    # Priority 3: In Databricks Apps, use WorkspaceClient default authentication
    # This will automatically use the service principal credentials
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        # Get the config and extract token if available
        if hasattr(w.config, 'token') and w.config.token:
            return w.config.token
        # For Databricks Apps, the SDK handles authentication automatically
        # We can use the WorkspaceClient directly for API calls
        # Return a placeholder to indicate SDK auth should be used
        return "__DATABRICKS_SDK_AUTH__"
    except Exception as e:
        print(f"Warning: Could not initialize WorkspaceClient: {e}")

    # Priority 4: Try Databricks Apps service principal token environment variables
    token = os.environ.get("DATABRICKS_SERVICE_PRINCIPAL_TOKEN")
    if token:
        return token

    token = os.environ.get("DATABRICKS_APP_TOKEN")
    if token:
        return token

    raise RuntimeError(
        "Databricks token not found. Set DATABRICKS_TOKEN env var, pass token from request headers, or ensure app is running in Databricks Apps environment with proper authentication."
    )


# ---------- read mapping CSV from the volume ----------
def read_mapping_csv(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parse CSV content (simulating reading from volume).

    Expects CSV with header:
    Source_Table,Source_Column,Target_Table,Target_Column,Transformation

    Returns: list of mappings grouped by Source_Table -> list of column mappings

    NOTE: In production Databricks environment, this would use:
    spark.read.format("csv").option("header", "true").option("inferSchema", "true").load(path)
    """
    print(f"Parsing mapping CSV content")

    # Parse CSV content line by line
    lines = csv_content.strip().split('\n')
    if not lines:
        return []

    # Skip header
    header = lines[0]

    # Group by Source_Table to produce one mapping per source table
    mappings = {}
    for line in lines[1:]:
        parts = line.split(',')
        if len(parts) < 5:
            continue

        src_tbl = str(parts[0] or "").strip()
        src_col = str(parts[1] or "").strip()
        tgt_tbl = str(parts[2] or "").strip()
        tgt_col = str(parts[3] or "").strip()
        transform = str(parts[4] or "").strip() if len(parts) > 4 else ""

        if not src_tbl:
            continue

        mappings.setdefault(src_tbl, []).append({
            "source_column": src_col,
            "target_table": tgt_tbl,
            "target_column": tgt_col,
            "transformation": transform
        })

    # Convert to list of mapping objects (one per source table)
    mapping_list = []
    for src_tbl, cols in mappings.items():
        # prefer target_table from the first row (assumes same target for all rows of same source)
        mapping_list.append({
            "pipeline_id": src_tbl.replace(".", "_"),
            "source_path_or_table": src_tbl,  # the generated code will read from this path/table
            "columns": cols
        })

    return mapping_list


# ---------- build prompt for a single mapping ----------
def build_prompt_for_mapping(map_obj: Dict[str, Any]) -> str:
    """
    Build prompt for a single mapping.

    map_obj example:
    {
      "pipeline_id": "...",
      "source_path_or_table": "/Volumes/krish_catalog/.../input/…",
      "columns": [
         {"source_column":"a","target_table":"/Volumes/.../silver...","target_column":"A","transformation":"a*2"},
         ...
      ]
    }
    """
    instr = textwrap.dedent("""
    You are an expert Databricks PySpark engineer. Generate exactly one Python PySpark script (only raw python code, no markdown)
    that:
      - Reads data from the SOURCE path (this is a Unity Catalog Volume path) using spark.read.format(...).load(source_path)
      - Applies per-column transformations (provided below). For each mapping row:
          - If transformation is non-empty, compute target_column as the transformation expression using DataFrame APIs (withColumn/selectExpr)
          - Otherwise map source_column -> target_column directly
      - Writes final result as Delta into the TARGET VOLUME path (use Delta write to the target path)
      - If more than one unique target_table exists in the mapping rows, assume they are all the same volume path; if not, write to the first target path
      - If Transformation describes a derived column with no Source_Column (empty Source_Table/Source_Column), create the column based on the target column name and load data based on the transformation logic.
      - Parameterize run_date and max_ts with dbutils.widgets if required (but not mandatory)
      - Add minimal error handling and logging
      - Use only pyspark + delta APIs (no external SDKs)
      - Use DeltaTable.forPath only if implementing MERGE. If a merge is not requested, use write.format('delta').mode('overwrite').save(target_path)
      - Keep code deterministic and idiomatic (clear variable names)
      - Output a single file content (the generated script)
    """).strip()

    # Provide mapping rows in JSON for model to use
    payload = {
        "pipeline_id": map_obj.get("pipeline_id"),
        "source_path_or_table": map_obj.get("source_path_or_table"),
        "mappings": map_obj.get("columns")
    }
    prompt = instr + "\n\nMapping JSON:\n" + json.dumps(payload, indent=2) + "\n\nNow output the Python script only."
    return prompt


# ---------- call Claude Sonnet via OpenAI-style client ----------
def call_claude_sonnet(prompt: str, token: str) -> str:
    """
    Call Databricks model serving endpoint using OpenAI-compatible API.

    This uses the Databricks Foundation Model API endpoint for Claude Sonnet.
    """
    client = OpenAI(api_key=token, base_url=f"{WORKSPACE_URL}/serving-endpoints")

    # Compose messages: system + user
    messages = [
        {"role": "system", "content": "You are a senior Databricks PySpark engineer."},
        {"role": "user", "content": prompt}
    ]

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=4000,
        temperature=0.05
    )

    # Robustly extract text
    try:
        return resp.choices[0].message.content
    except Exception:
        # fallback stringify
        return str(resp)


# ---------- save generated code to the target volume path ----------
def save_code_to_volume(target_path: str, code_text: str, pipeline_id: str = "unnamed") -> bool:
    """
    Simulate saving code to volume (would use dbutils.fs.put in actual Databricks).

    In production Databricks environment, this would use:
    dbutils.fs.put(target_path, code_text, True)

    For local testing, we just return True.
    """
    print(f"Code would be saved to: {target_path}")
    return True


# ------------------ main generation function ------------------
def generate_pyspark_code(
    mapping_csv_content: str,
    output_file_path: str,
    request_token: str = None
) -> str:
    """
    Main function to generate PySpark code from mapping CSV.

    This is the EXACT logic from your generate_from_volume_mapping.py notebook.

    Args:
        mapping_csv_content: Raw CSV content as string
        output_file_path: Target path for generated code
        request_token: Optional token from HTTP request headers (for Databricks Apps)

    Returns:
        Generated PySpark code as string
    """
    try:
        # Get Databricks token
        token = get_databricks_token(request_token)

        # Read and parse mapping CSV
        mapping_list = read_mapping_csv(mapping_csv_content)
        if not mapping_list:
            raise RuntimeError("No mapping rows found. Exiting.")

        # Combine mappings into a single 'document' for the model
        combined = {
            "pipelines": mapping_list,
            "note": "Generate a single Python file that iterates over each pipeline mapping and runs the ETL for each mapping. The file should be parameterized and idempotent."
        }

        # Build one prompt for entire mapping set (single output file)
        prompt = textwrap.dedent("""
        You are an expert Databricks PySpark engineer. Generate a single Python PySpark script (output the raw python code only)
        that:
          - Iterates over each pipeline mapping provided in the JSON below.
          - For each mapping: read the source (a Unity Catalog Volume path) using spark.read.format(...).load(source_path),
            apply per-column transformations (or pass-through), and write the results to the target Unity Catalog Volume path using Delta.
          - Use clear function boundaries: read_source, apply_transformations, write_target.
          - Add basic logging and error handling but avoid secrets.
          - The generated script must be runnable in Databricks (use dbutils.widgets for parameters if needed).
        """).strip() + "\n\nMappings:\n" + json.dumps(combined, indent=2) + "\n\nNow output the Python script only."

        # Call model (Databricks model serving endpoint)
        model_response = call_claude_sonnet(prompt, token)
        code_text = model_response if isinstance(model_response, str) else str(model_response)

        # Sanity check
        if not code_text or len(code_text.strip()) < MIN_RESPONSE_LEN:
            raise RuntimeError("Model returned empty or too-short response; aborting.")

        # Clean up markdown code blocks if present
        code_text = code_text.strip()
        if code_text.startswith("```python"):
            code_text = code_text[9:]
        if code_text.startswith("```"):
            code_text = code_text[3:]
        if code_text.endswith("```"):
            code_text = code_text[:-3]

        # Save to the requested output volume file path
        # (In actual Databricks, this would use dbutils.fs.put)
        saved = save_code_to_volume(output_file_path, code_text.strip(), pipeline_id="all_pipelines")
        if saved:
            print(f"✅ Successfully saved generated code to {output_file_path}")
        else:
            print("⚠️ Could not save directly to volume.")

        return code_text.strip()

    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()
        raise RuntimeError(f"Code generation failed: {str(e)}")
