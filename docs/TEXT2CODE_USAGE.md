# Text2Code Generator - Usage Guide

## Overview

Text2Code Generator is a web-based application that automatically generates production-ready PySpark ETL code from CSV mapping specifications using Claude Sonnet 4.5 via Databricks Foundation Model API.

## Features

- **Two Data Source Options**:
  - **Unity Catalog Volume**: Upload mapping CSV from UC Volume paths (fully functional)
  - **JIRA Integration**: Coming soon (work in progress)

- **Three ETL Patterns**:
  - **PySpark ETL**: Standard PySpark ETL with transformations and Delta write
  - **Delta MERGE (Upsert)**: Upsert pattern using Delta MERGE operation
  - **SCD Type 2**: Slowly Changing Dimension Type 2 with history tracking

- **Customizable Prompt Templates**: Override default patterns with your own custom prompt

## How to Use

### 1. Start the Application

```bash
# Start development servers
./watch.sh
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 2. Using the Web Interface

1. **Select Data Source**:
   - Choose "Unity Catalog Volume" tab
   - Enter the full path to your mapping CSV in UC Volume
   - Example: `/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv`

2. **Select ETL Pattern**:
   - Choose from: PySpark ETL, Delta MERGE, or SCD Type 2
   - Each pattern generates different code optimized for the use case

3. **Optional: Custom Prompt**:
   - Leave blank to use the default prompt for the selected pattern
   - Or enter a custom prompt template to fully customize the generation

4. **Generate Code**:
   - Click "Generate Code" button
   - Wait for Claude Sonnet to generate the code (typically 10-30 seconds)
   - View the generated PySpark code in the preview panel

5. **Copy or Download**:
   - Click "Copy Code" to copy to clipboard
   - Save the code to a file for deployment

### 3. Mapping CSV Format

Your mapping CSV should follow this format:

```csv
Source_Table,Source_Column,Target_Table,Target_Column,Transformation
/Volumes/catalog/schema/volume/input/sales.parquet,order_id,/Volumes/catalog/schema/volume/output/orders,order_key,
/Volumes/catalog/schema/volume/input/sales.parquet,amount,/Volumes/catalog/schema/volume/output/orders,total_amount,amount * 1.1
/Volumes/catalog/schema/volume/input/sales.parquet,order_date,/Volumes/catalog/schema/volume/output/orders,order_timestamp,to_timestamp(order_date)
```

**Column Definitions**:
- `Source_Table`: Full path to source table/file in Unity Catalog Volume
- `Source_Column`: Source column name (leave empty for derived columns)
- `Target_Table`: Full path to target table/location in Unity Catalog Volume
- `Target_Column`: Target column name
- `Transformation`: Optional transformation expression (leave empty for direct mapping)

## API Usage

### Get Available Patterns

```bash
curl http://localhost:8000/api/code/patterns
```

### Generate Code

```bash
curl -X POST "http://localhost:8000/api/code/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv",
    "pattern": "pyspark"
  }'
```

### Generate Code with Custom Prompt

```bash
curl -X POST "http://localhost:8000/api/code/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv",
    "pattern": "pyspark",
    "custom_prompt": "Generate a PySpark script with extensive error handling and logging"
  }'
```

## Custom Prompt Templates

You can customize the code generation by providing your own prompt template. The prompt should instruct Claude Sonnet on:

- How to read the source data
- What transformations to apply
- How to write the target data
- Any special requirements (error handling, logging, parameterization, etc.)

**Example Custom Prompt**:

```
You are an expert Databricks PySpark engineer. Generate a Python PySpark script that:
  - Reads data from Unity Catalog Volume paths
  - Applies the provided column transformations
  - Includes comprehensive error handling with try/except blocks
  - Logs all operations using Python logging
  - Uses dbutils.widgets for parameterization
  - Writes to Delta format with proper partition strategy
  - Includes unit test examples
  - Follows PEP 8 style guidelines

Output only the raw Python code, no markdown.
```

## Generated Code Features

All generated code includes:

- ✅ Reading from Unity Catalog Volume paths
- ✅ Column transformations and business logic
- ✅ Writing to Delta format
- ✅ Error handling and logging
- ✅ Parameterization with dbutils.widgets
- ✅ Idempotent execution logic
- ✅ Clean, well-documented code

Pattern-specific features:

- **PySpark ETL**: Standard overwrite mode
- **Delta MERGE**: Upsert logic with proper merge keys
- **SCD Type 2**: History tracking with effective dates

## Environment Variables

The backend requires these environment variables (configured in `.env.local`):

```bash
DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
DATABRICKS_TOKEN=dapi...
```

## Testing

Run the comprehensive test script:

```bash
./claude_scripts/test_code_generation.sh
```

This will test all patterns and scenarios, including:
- Fetching available patterns
- Generating code with PySpark pattern
- Generating code with MERGE pattern
- Testing JIRA source (returns 501)
- Generating code with custom prompt

## Architecture

**Backend** (FastAPI + Python):
- `/server/routers/generate.py`: API endpoints for code generation
- `/server/services/code_generator.py`: Core logic for Claude API integration
- Uses OpenAI Python SDK with Databricks Foundation Model API

**Frontend** (React + TypeScript):
- `/client/src/pages/Text2CodePage.tsx`: Main UI component
- shadcn/ui components for modern UI
- Real-time code generation with loading states

**Model**:
- Claude Sonnet 4.5 via Databricks Foundation Model API
- Temperature: 0.05 (deterministic output)
- Max tokens: 4000

## Troubleshooting

### Backend not starting
```bash
# Check uvicorn logs
tail -f /tmp/uvicorn.log

# Restart backend
kill $(pgrep -f uvicorn)
uv run uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend not loading
```bash
# Check Vite logs
tail -f /tmp/vite-dev.log

# Restart frontend
cd client && bun run dev
```

### API authentication errors
Ensure your `.env.local` has valid Databricks credentials:
```bash
source .env.local
echo $DATABRICKS_HOST
echo $DATABRICKS_TOKEN
```

## Next Steps

- Deploy the application to Databricks Apps using `./deploy.sh`
- Create additional custom prompt templates for your organization
- Integrate with JIRA (coming soon)
- Add unit test generation
- Implement code history and version tracking
