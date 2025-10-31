#!/bin/bash
# Test script for Text2Code Generator API

echo "Testing Text2Code Generator API"
echo "================================"
echo ""

# Test 1: Get available patterns
echo "1. Fetching available patterns..."
curl -s http://localhost:8000/api/code/patterns | jq
echo ""

# Test 2: Generate code with PySpark pattern
echo "2. Generating code with PySpark pattern..."
curl -s -X POST "http://localhost:8000/api/code/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv",
    "pattern": "pyspark"
  }' | jq -r '.message'
echo ""

# Test 3: Generate code with MERGE pattern
echo "3. Generating code with MERGE pattern..."
curl -s -X POST "http://localhost:8000/api/code/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv",
    "pattern": "merge"
  }' | jq -r '.message'
echo ""

# Test 4: Test JIRA source (should return 501)
echo "4. Testing JIRA source (work in progress)..."
curl -s -X POST "http://localhost:8000/api/code/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "jira",
    "pattern": "pyspark"
  }' | jq
echo ""

# Test 5: Generate code with custom prompt
echo "5. Generating code with custom prompt..."
curl -s -X POST "http://localhost:8000/api/code/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv",
    "pattern": "pyspark",
    "custom_prompt": "Generate a very simple PySpark script that reads CSV, applies basic transformations, and writes to Delta. Include extensive comments explaining each step."
  }' | jq -r '.message'
echo ""

echo "✅ All tests completed!"
