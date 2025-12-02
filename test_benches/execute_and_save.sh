#!/bin/bash

# Execute a Python script and save output to a file
# Usage: ./execute_and_save.sh <python_file> <output_dir>
# Example: ./execute_and_save.sh ../messages_latency.py ./results

# Check if arguments are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <python_file> <output_dir>"
    echo "Example: $0 ../messages_latency.py ./results"
    exit 1
fi

PYTHON_FILE="$1"
OUTPUT_DIR="$2"

# Check if the Python file exists
if [ ! -f "$PYTHON_FILE" ]; then
    echo "Error: Python file '$PYTHON_FILE' not found"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate output filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BASENAME=$(basename "$PYTHON_FILE" .py)
OUTPUT_FILE="${OUTPUT_DIR}/${BASENAME}_${TIMESTAMP}.txt"

echo "=================================="
echo "Executing: $PYTHON_FILE"
echo "Output will be saved to: $OUTPUT_FILE"
echo "=================================="

# Execute the Python script and save output (both stdout and stderr)
python "$PYTHON_FILE" 2>&1 | tee "$OUTPUT_FILE"

echo ""
echo "=================================="
echo "Execution complete!"
echo "Output saved to: $OUTPUT_FILE"
echo "=================================="