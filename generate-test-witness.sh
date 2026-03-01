#!/bin/bash

# Test witness generation script
# Generates a test barcode, decodes it, and creates witness files

# Parameters
WITNESS_DIR="${1:-test-witness}"
ROWS=3
COLS=2
EC=1
BARCODE_FILE="$WITNESS_DIR/pdf417_r${ROWS}_c${COLS}_e${EC}.png"
WITNESS_FILE="$WITNESS_DIR/witness_r${ROWS}_c${COLS}_e${EC}.json"
WITNESS_PIN="$WITNESS_DIR/witness_r${ROWS}_c${COLS}_e${EC}.pin"
WITNESS_VIN="$WITNESS_DIR/witness_r${ROWS}_c${COLS}_e${EC}.vin"

MOD=52435875175126190479447740508185965837690552500527637822603658699938581184513

echo "Test Witness Generation"
echo "======================"
echo "Parameters: ROWS=$ROWS, COLS=$COLS, EC=$EC, WITNESS_DIR=$WITNESS_DIR"
echo ""

# Check if inside virtual environment
if ! python -c 'import sys; exit(0 if sys.prefix != sys.base_prefix else 1)'; then
    echo "Error: Not inside a virtual environment; exiting."
    echo "Please activate a virtual environment and try again."
    exit 1
fi
PYTHON_BIN=$(python -c 'import sys; print(sys.executable)')

# Create/wipe witness directory
echo "Preparing $WITNESS_DIR directory..."
rm -rf "$WITNESS_DIR"
mkdir -p "$WITNESS_DIR"
echo "✓ Directory ready"
echo ""

# Step 1: Generate barcode
echo "Step 1: Generating barcode..."
${PYTHON_BIN} python-scripts/generate-barcode.py -r $ROWS -c $COLS -e $EC -o "$BARCODE_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to generate barcode"
    exit 1
fi
echo "✓ Barcode generated: $BARCODE_FILE"
echo ""

# Step 2: Decode barcode and generate witness
echo "Step 2: Decoding barcode and generating witness..."
cd external/rxing
cargo run -p rxing-cli -- "../../$BARCODE_FILE" decode --save-witness "../../$WITNESS_FILE" --barcode-types PDF_417
if [ $? -ne 0 ]; then
    echo "Error: Failed to decode barcode"
    cd ../..
    exit 1
fi
cd ../..
echo "✓ Witness generated: $WITNESS_FILE"
echo ""

# Step 3: Convert witness JSON to witness files
echo "Step 3: Converting witness JSON to .pin and .vin files..."
${PYTHON_BIN} python-scripts/json_to_witness.py \
    -i "$WITNESS_FILE" \
    --map bin_image=binarized_image \
    --map image=image \
    --type bin_image=bool \
    --modulus "$MOD" \
    --pin "$WITNESS_PIN" \
    --vin "$WITNESS_VIN"
if [ $? -ne 0 ]; then
    echo "Error: Failed to convert witness JSON"
    exit 1
fi
echo "✓ Witness files generated:"
echo "  - $WITNESS_PIN"
echo "  - $WITNESS_VIN"
echo ""

echo "========================================"
echo "✓ Test witness generation complete!"
echo "========================================"
echo ""
echo "Generated files in $WITNESS_DIR/:"
ls -lh "$WITNESS_DIR/"
