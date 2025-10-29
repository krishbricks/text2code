"""Code generation service using Claude Sonnet via Databricks."""

import os
import json
import textwrap
from typing import Optional
from openai import OpenAI


class CodeGenerator:
    """Generate PySpark code from mapping CSV using Claude Sonnet."""

    def __init__(self):
        """Initialize the code generator with Databricks credentials."""
        self.workspace_url = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
        self.token = os.environ.get("DATABRICKS_TOKEN", "")
        self.model_name = "databricks-claude-sonnet-4-5"

        # Ensure workspace URL has https:// prefix
        if self.workspace_url and not self.workspace_url.startswith("http://") and not self.workspace_url.startswith("https://"):
            self.workspace_url = f"https://{self.workspace_url}"

        if not self.workspace_url or not self.token:
            raise RuntimeError(
                "DATABRICKS_HOST and DATABRICKS_TOKEN environment variables must be set"
            )

        self.client = OpenAI(
            api_key=self.token,
            base_url=f"{self.workspace_url}/serving-endpoints"
        )

    def _get_default_prompt_template(self, pattern: str) -> str:
        """Get the default prompt template for a given pattern."""

        if pattern == "pyspark":
            return textwrap.dedent("""
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

        elif pattern == "merge":
            return textwrap.dedent("""
            You are an expert Databricks PySpark engineer. Generate exactly one Python PySpark script (only raw python code, no markdown)
            that implements a Delta MERGE (upsert) pattern:
              - Reads data from the SOURCE path (Unity Catalog Volume) using spark.read.format(...).load(source_path)
              - Applies per-column transformations (provided below)
              - Uses DeltaTable.forPath to perform MERGE operation on target table
              - Implements proper merge keys (primary keys) for matching records
              - Updates existing records and inserts new ones
              - Add minimal error handling and logging
              - Use only pyspark + delta APIs
              - Keep code deterministic and idiomatic
              - Output a single file content (the generated script)
            """).strip()

        elif pattern == "scd2":
            return textwrap.dedent("""
            You are an expert Databricks PySpark engineer. Generate exactly one Python PySpark script (only raw python code, no markdown)
            that implements a Slowly Changing Dimension Type 2 pattern:
              - Reads data from the SOURCE path (Unity Catalog Volume) using spark.read.format(...).load(source_path)
              - Applies per-column transformations (provided below)
              - Implements SCD Type 2 logic with history tracking:
                  - Add effective_start_date, effective_end_date, is_current columns
                  - Expire old records by setting effective_end_date and is_current=False
                  - Insert new records with effective_start_date=current_date, is_current=True
              - Uses Delta MERGE for efficient SCD updates
              - Add minimal error handling and logging
              - Use only pyspark + delta APIs
              - Keep code deterministic and idiomatic
              - Output a single file content (the generated script)
            """).strip()

        else:
            return textwrap.dedent("""
            You are an expert Databricks PySpark engineer. Generate exactly one Python PySpark script (only raw python code, no markdown)
            that processes data from a Unity Catalog Volume path and writes to a target Volume path using Delta format.
            Apply the provided column mappings and transformations.
            """).strip()

    async def generate_from_volume(
        self,
        volume_path: str,
        pattern: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Generate PySpark code from a mapping CSV in a Unity Catalog Volume.

        Args:
            volume_path: Path to the mapping CSV in Unity Catalog Volume
            pattern: ETL pattern to use (pyspark, merge, scd2)
            custom_prompt: Optional custom prompt template to override default

        Returns:
            Generated PySpark code as a string
        """

        # Use custom prompt if provided, otherwise use default template
        prompt_template = custom_prompt or self._get_default_prompt_template(pattern)

        # Build the complete prompt
        prompt = textwrap.dedent(f"""
        {prompt_template}

        Mapping CSV Path: {volume_path}

        Generate the complete PySpark script that:
        1. Reads the mapping CSV from the volume path: {volume_path}
        2. Groups mappings by Source_Table
        3. For each source table:
           - Read source data from the volume path
           - Apply column transformations
           - Write to target volume path using Delta format
        4. Include proper error handling and logging
        5. Make the script parameterizable with dbutils.widgets

        Output only the Python code, no markdown formatting.
        """).strip()

        # Call Claude Sonnet API
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior Databricks PySpark engineer specializing in ETL pipelines."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.05
            )

            # Extract code from response
            code = response.choices[0].message.content

            # Basic validation
            if not code or len(code.strip()) < 40:
                raise RuntimeError("Model returned empty or too-short response")

            # Clean up markdown code blocks if present
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]

            return code.strip()

        except Exception as e:
            raise RuntimeError(f"Failed to generate code: {str(e)}")
