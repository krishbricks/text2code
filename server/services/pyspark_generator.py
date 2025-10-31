"""
PySpark code generation service - EXACT logic from generate_from_volume_mapping.py
Using the proven notebook code directly.
"""

import os
import json
import tempfile
import textwrap
import traceback
from openai import OpenAI
from typing import Dict, List, Any, Optional
import pandas as pd
from databricks.sdk import WorkspaceClient

# ------------------ CONFIG ------------------
WORKSPACE_URL = "https://adb-315278363237056.16.azuredatabricks.net"
MODEL_NAME = "databricks-claude-sonnet-4-5"
MIN_RESPONSE_LEN = 40

# ---------- obtain Databricks PAT ----------
def get_databricks_token(request_token: str = None):
    """Get Databricks token from various sources."""
    if request_token:
        return request_token

    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return token

    # Hardcode for testing
    print("⚠️  WARNING: Using hardcoded token for testing")
    return ""

# ---------- download file from volume to local disk ----------
def download_file_from_volume(volume_file_path: str, destination_dir: str = None) -> str:
    """
    Downloads a file from a Unity Catalog volume using Files API and saves to local disk.
    Returns the local file path.

    volume_file_path example: "/Volumes/my_catalog/my_schema/my_volume/mapping.csv"
    """
    try:
        print(f"Downloading file from volume: {volume_file_path}")

        if destination_dir is None:
            destination_dir = tempfile.mkdtemp()

        os.makedirs(destination_dir, exist_ok=True)
        local_path = os.path.join(destination_dir, os.path.basename(volume_file_path))

        # Use Files API's download() and extract content
        w = WorkspaceClient()
        response = w.files.download(file_path=volume_file_path)

        print(f"DEBUG: Download response type: {type(response)}")
        all_attrs = [a for a in dir(response) if not a.startswith('_')]
        print(f"DEBUG: All response attributes: {all_attrs}")

        content = None

        # Method 1: Try .contents attribute - it's a file-like object!
        try:
            if hasattr(response, 'contents'):
                contents_attr = response.contents
                print(f"DEBUG: .contents attribute found (type: {type(contents_attr)})")

                # .contents is a file-like object - call .read() to get the data
                if hasattr(contents_attr, 'read') and callable(contents_attr.read):
                    try:
                        print(f"DEBUG: Calling .read() on file-like .contents object...")
                        data = contents_attr.read()
                        print(f"DEBUG: .read() returned type: {type(data)}, size: {len(data) if hasattr(data, '__len__') else '?'}")

                        if isinstance(data, bytes):
                            content = data
                            print(f"DEBUG: ✅ Got {len(content)} bytes from .contents.read()")
                        elif isinstance(data, str):
                            content = data
                            print(f"DEBUG: ✅ Got {len(content)} chars from .contents.read()")
                        else:
                            print(f"DEBUG: .read() returned unexpected type: {type(data)}")
                    except Exception as read_e:
                        print(f"DEBUG: .read() failed: {type(read_e).__name__}: {read_e}")
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            print(f"DEBUG: .contents access failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        # Final check - if we still don't have content, extraction failed
        if content is None:
            raise RuntimeError(f"Could not extract content from file. Response type: {type(response)}. Available attributes: {all_attrs}")

        print(f"DEBUG: Content type before conversion: {type(content)}")

        # Convert bytes to string if needed
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
                print(f"DEBUG: ✅ Decoded bytes to string ({len(content)} chars)")
            except Exception as e:
                print(f"DEBUG: Decode failed: {e}")
                raise

        # Final type check before writing
        if not isinstance(content, str):
            raise RuntimeError(f"Content is {type(content)}, expected str after all conversions. Available attributes tried: {all_attrs}. Content preview: {str(content)[:200]}")

        # Write to local file
        print(f"DEBUG: Writing {len(content)} characters to {local_path}")
        with open(local_path, 'w') as f:
            f.write(content)

        file_size = os.path.getsize(local_path)
        print(f"✅ File downloaded and saved to: {local_path} ({file_size} bytes)")
        return local_path

    except Exception as e:
        print(f"ERROR downloading file from {volume_file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Failed to download file from {volume_file_path}: {str(e)}")


# ---------- read mapping CSV from local file using pandas ----------
def read_mapping_csv_from_local(local_csv_path: str) -> List[Dict[str, Any]]:
    """
    Read the mapping CSV from a local file path using pandas.
    Expects CSV with header:
    Source_Table,Source_Column,Target_Table,Target_Column,Transformation
    """
    try:
        print(f"Reading mapping CSV from local file: {local_csv_path}")

        EXPECTED_COLS = {"Source_Table", "Source_Column", "Target_Table", "Target_Column", "Transformation"}

        # Read with pandas for simplicity and predictable behavior in app runtime
        df = pd.read_csv(local_csv_path, dtype=str).fillna("")

        # Normalize column names (strip)
        df.columns = [c.strip() for c in df.columns]

        present = set(df.columns)
        missing = EXPECTED_COLS - present
        if missing:
            raise ValueError(f"Mapping CSV is missing expected columns: {missing}. Present columns: {present}")

        # Trim whitespace on relevant columns
        for col in EXPECTED_COLS:
            df[col] = df[col].astype(str).str.strip().fillna("")

        # Filter out empty Source_Table rows
        df = df[df["Source_Table"].astype(bool)]

        print(f"DEBUG: Loaded {len(df)} mapping rows")

        # Group by Source_Table
        mapping_list = []
        grouped = df.groupby("Source_Table", sort=False)

        for src_tbl, group in grouped:
            cols = []
            first_target = ""

            for _, row in group.iterrows():
                src_col = row["Source_Column"] or ""
                tgt_tbl = row["Target_Table"] or ""
                tgt_col = row["Target_Column"] or ""
                transform = row.get("Transformation") or ""

                if not first_target and tgt_tbl:
                    first_target = tgt_tbl

                cols.append({
                    "source_column": src_col,
                    "target_table": tgt_tbl,
                    "target_column": tgt_col,
                    "transformation": transform
                })

            mapping_list.append({
                "pipeline_id": src_tbl.replace(".", "_"),
                "source_path_or_table": src_tbl,
                "target_table_hint": first_target,
                "columns": cols
            })

        print(f"DEBUG: Created {len(mapping_list)} mapping objects")
        return mapping_list

    except Exception as e:
        print(f"ERROR reading CSV from {local_csv_path}: {e}")
        raise RuntimeError(f"Failed to read mapping CSV from {local_csv_path}: {str(e)}")


# ---------- read mapping from volume path ----------
def read_mapping_csv(volume_path: str) -> List[Dict[str, Any]]:
    """
    High-level helper: download file from Files API path (volume) and parse mapping.

    volume_path examples:
      - "/Volumes/my_catalog/my_schema/my_volume/mapping.csv"
      - "/Volumes/my_catalog/my_schema/my_volume/folder/" (must be exact file path)
    """
    try:
        # 1) Download via SDK to local disk (handles streaming internally)
        local_csv = download_file_from_volume(volume_path)

        # 2) Parse local CSV with pandas
        return read_mapping_csv_from_local(local_csv)

    except Exception as e:
        print(f"ERROR in read_mapping_csv: {e}")
        raise RuntimeError(f"Failed to read mapping from {volume_path}: {str(e)}")

# ---------- call Claude Sonnet via OpenAI-style client ----------
def call_claude_sonnet(prompt: str, token: str) -> str:
    """
    Call Databricks model serving endpoint using OpenAI-compatible API.
    Handles both non-streaming and streaming responses robustly.
    """
    if not token:
        raise RuntimeError(
            "No valid Databricks token provided. "
            "Please set DATABRICKS_TOKEN environment variable."
        )

    client = OpenAI(
        api_key=token,
        base_url=f"{WORKSPACE_URL}/serving-endpoints"
    )

    messages = [
        {"role": "system", "content": "You are a senior Databricks PySpark engineer."},
        {"role": "user", "content": prompt}
    ]

    # Request a non-streaming response explicitly (avoid streaming object)
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=4000,
            temperature=0.05,
            stream=False   # <-- force non-streaming response when possible
        )
    except TypeError:
        # Some client versions use 'stream' differently; try without stream argument
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=4000,
            temperature=0.05
        )

    print(f"DEBUG: Response type = {type(resp)}")
    print(f"DEBUG: Response dir = {dir(resp)[:10]}")  # Show first 10 attributes
    print(f"DEBUG: Response repr = {repr(resp)[:200]}")  # Show first 200 chars of repr

    # 1) Try the normal non-streaming extraction
    try:
        # many clients: resp.choices[0].message.content
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            first = resp.choices[0]
            print(f"DEBUG: first choice type = {type(first)}")
            print(f"DEBUG: first choice dir = {dir(first)[:10]}")

            # prefer .message.content if present
            if hasattr(first, "message") and getattr(first.message, "content", None) is not None:
                content = first.message.content
                if isinstance(content, str):
                    print(f"DEBUG: ✅ Got string content, length = {len(content)}")
                    return content
                else:
                    print(f"DEBUG: content type is {type(content)}, not str")
            # fallback to .text or similar
            if getattr(first, "text", None) is not None:
                content = first.text
                if isinstance(content, str):
                    print(f"DEBUG: ✅ Got .text content, length = {len(content)}")
                    return content
                else:
                    print(f"DEBUG: .text type is {type(content)}, not str")
        else:
            print(f"DEBUG: No choices attribute or empty choices")
    except Exception as e:
        print(f"DEBUG: Non-streaming extraction failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # 2) If we got here, the client might have returned a streaming object.
    # Try to iterate/collect text chunks from it.
    try:
        print(f"DEBUG: Attempting streaming extraction...")
        collected_parts = []
        chunk_count = 0

        # Some streaming responses are iterable
        if hasattr(resp, "__iter__") and not isinstance(resp, (str, bytes)):
            print(f"DEBUG: Response is iterable, attempting to collect chunks...")
            try:
                for chunk in resp:
                    chunk_count += 1
                    print(f"DEBUG: Chunk {chunk_count} type = {type(chunk)}")

                    try:
                        # chunk might be a dict-like or object with .choices
                        if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                            c0 = chunk.choices[0]
                            # streaming delta path: c0.delta.get('content')
                            delta = getattr(c0, "delta", None)
                            if isinstance(delta, dict):
                                part = delta.get("content")
                            else:
                                part = getattr(delta, "content", None)
                            if part:
                                print(f"DEBUG: Got delta content: {part[:50]}...")
                                collected_parts.append(part)
                            # some streaming chunks put text in c0.text
                            if getattr(c0, "text", None):
                                print(f"DEBUG: Got chunk text")
                                collected_parts.append(c0.text)
                        # chunk could be a plain dict
                        elif isinstance(chunk, dict):
                            print(f"DEBUG: Chunk is dict, processing...")
                            # try nested shapes
                            for ch in chunk.get("choices", []):
                                if "delta" in ch and "content" in ch["delta"]:
                                    collected_parts.append(ch["delta"]["content"])
                                elif "text" in ch:
                                    collected_parts.append(ch["text"])
                    except Exception as chunk_err:
                        # ignore malformed chunk and continue
                        print(f"DEBUG: Chunk processing error: {chunk_err}")
                        continue

                print(f"DEBUG: Collected {chunk_count} chunks with {len(collected_parts)} parts")
            except Exception as iter_err:
                print(f"DEBUG: Iteration error: {iter_err}")
        else:
            print(f"DEBUG: Response is NOT iterable (or is str/bytes)")

        if collected_parts:
            content = "".join(collected_parts)
            print(f"DEBUG: ✅ Collected streaming content, length = {len(content)}")
            return content
        else:
            print(f"DEBUG: No parts collected from streaming")

    except Exception as e:
        print(f"DEBUG: Streaming extraction exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # 3) Last resort: stringify resp if it gives a useful representation
    try:
        print(f"DEBUG: Attempting fallback stringify...")
        s = str(resp)
        print(f"DEBUG: Stringified response length = {len(s)}")
        print(f"DEBUG: Stringified response first 200 chars: {s[:200]}")

        if isinstance(s, str) and len(s) > 0:
            # Check if the stringified response looks valid (not just <_StreamingResponse...>)
            if s.startswith('<_StreamingResponse') or s.startswith('<Stream'):
                print(f"DEBUG: ❌ Stringified response is just a repr, not actual content")
                print(f"DEBUG: Would be using: {s[:100]}")
            else:
                print(f"DEBUG: ✅ Returning stringified response as fallback")
                return s
    except Exception as e:
        print(f"DEBUG: Fallback stringify failed: {type(e).__name__}: {e}")

    print(f"DEBUG: ❌ ALL extraction methods failed!")
    raise RuntimeError("Failed to extract valid string response from model. Response type was: " + str(type(resp)))

# ---------- save generated code to the target volume path ----------
def save_code_to_volume(target_path: str, code_text: str, pipeline_id: str = "unnamed") -> bool:
    """
    Save code to UC Volume using Databricks SDK.
    """
    print(f"Saving generated code to: {target_path}")
    try:
        w = WorkspaceClient()
        w.files.upload(
            target_path,
            code_text.encode('utf-8'),
            overwrite=True
        )
        print(f"✅ Saved via files.upload -> {target_path}")
        return True
    except Exception as e:
        print(f"Error saving code: {e}")
        return False

# ---------- main generation function ----------
def generate_pyspark_code(
    mapping_csv_content: str = None,
    input_volume_path: str = None,
    request_token: str = None
) -> str:
    """
    Main function to generate PySpark code from mapping CSV.
    Accepts either:
      - mapping_csv_content: CSV content as string (writes to temp file)
      - input_volume_path: Path to CSV file in UC Volume

    Returns generated code directly to UI.
    """
    try:
        # Get Databricks token
        token = get_databricks_token(request_token)

        # Get mapping list from either source
        if input_volume_path:
            print(f"Reading mapping from volume: {input_volume_path}")
            mapping_list = read_mapping_csv(input_volume_path)
        elif mapping_csv_content:
            print(f"Reading mapping from provided CSV content ({len(mapping_csv_content)} bytes)")
            # Write to temp file and read with pandas
            temp_dir = tempfile.mkdtemp()
            temp_csv_path = os.path.join(temp_dir, "mapping.csv")
            with open(temp_csv_path, 'w') as f:
                f.write(mapping_csv_content)
            mapping_list = read_mapping_csv_from_local(temp_csv_path)
        else:
            raise RuntimeError("Either mapping_csv_content or input_volume_path must be provided")

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

        # Call model (EXACT WORKING CODE)
        model_response = call_claude_sonnet(prompt, token)
        code_text = model_response if isinstance(model_response, str) else str(model_response)

        # Sanity check
        if not code_text or len(code_text) < MIN_RESPONSE_LEN:
            raise RuntimeError("Model returned empty or too-short response; aborting.")

        # Return crude response as-is - no stripping or cleanup
        print(f"✅ Code generation successful!")
        print(f"   Code length: {len(code_text)} characters")

        return code_text

    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()
        raise RuntimeError(f"Code generation failed: {str(e)}")
