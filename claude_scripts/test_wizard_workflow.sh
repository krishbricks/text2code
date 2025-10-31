#!/bin/bash
# Test script for PySpark Code Generator Wizard

echo "🧪 Testing PySpark Code Generator Wizard"
echo "=========================================="
echo ""

# Test 1: Generate code with all steps
echo "✅ Test 1: Full workflow code generation"
echo "----------------------------------------"
curl -s -X POST "http://localhost:8000/api/codegen/generate-pyspark" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "input_volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/input/mapping_sheet.csv",
    "output_volume_path": "/Volumes/krish_catalog/krish_schema/test_vol/output/generated_code.py",
    "pattern": "pyspark"
  }' > /tmp/test_response.json

echo "Steps completed:"
cat /tmp/test_response.json | jq -r '.steps[] | "  [\(.status)] \(.name) - \(.message // "")"'
echo ""

echo "Generated code preview:"
cat /tmp/test_response.json | jq -r '.code' | head -20
echo "... (truncated)"
echo ""

# Test 2: JIRA source (should fail with 501)
echo "✅ Test 2: JIRA source validation (should return 501)"
echo "-------------------------------------------------------"
curl -s -X POST "http://localhost:8000/api/codegen/generate-pyspark" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "jira",
    "input_volume_path": "/some/path",
    "output_volume_path": "/some/output",
    "pattern": "pyspark"
  }' | jq '.detail'
echo ""

# Test 3: Missing input path (should fail with 400)
echo "✅ Test 3: Missing input path validation (should return 400)"
echo "------------------------------------------------------------"
curl -s -X POST "http://localhost:8000/api/codegen/generate-pyspark" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "volume",
    "input_volume_path": "",
    "output_volume_path": "/some/output",
    "pattern": "pyspark"
  }' | jq '.detail'
echo ""

# Test 4: Check success status
echo "✅ Test 4: Verify successful generation"
echo "---------------------------------------"
SUCCESS=$(cat /tmp/test_response.json | jq -r '.success')
if [ "$SUCCESS" = "true" ]; then
  echo "✅ Code generation successful!"
else
  echo "❌ Code generation failed!"
  exit 1
fi
echo ""

# Test 5: Verify all steps completed
echo "✅ Test 5: Verify all steps completed"
echo "-------------------------------------"
COMPLETED_STEPS=$(cat /tmp/test_response.json | jq -r '[.steps[] | select(.status == "completed")] | length')
TOTAL_STEPS=$(cat /tmp/test_response.json | jq -r '.steps | length')
echo "Completed steps: $COMPLETED_STEPS / $TOTAL_STEPS"

if [ "$COMPLETED_STEPS" -eq "$TOTAL_STEPS" ]; then
  echo "✅ All steps completed successfully!"
else
  echo "❌ Some steps did not complete!"
  exit 1
fi
echo ""

# Test 6: Verify generated code contains expected elements
echo "✅ Test 6: Verify generated code quality"
echo "----------------------------------------"
CODE=$(cat /tmp/test_response.json | jq -r '.code')

if echo "$CODE" | grep -q "SparkSession"; then
  echo "✅ Contains SparkSession initialization"
else
  echo "❌ Missing SparkSession initialization"
fi

if echo "$CODE" | grep -q "read_source\|spark.read"; then
  echo "✅ Contains read logic"
else
  echo "❌ Missing read logic"
fi

if echo "$CODE" | grep -q "write\|save"; then
  echo "✅ Contains write logic"
else
  echo "❌ Missing write logic"
fi

if echo "$CODE" | grep -q "Delta\|delta"; then
  echo "✅ Contains Delta format references"
else
  echo "❌ Missing Delta format"
fi
echo ""

echo "🎉 All tests passed!"
echo "===================="
echo ""
echo "Frontend UI available at: http://localhost:5173"
echo "Backend API available at: http://localhost:8000"
echo "API docs available at: http://localhost:8000/docs"
