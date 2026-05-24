#!/bin/bash

set -euo pipefail

# ── Hardcoded benchmark parameters ───────────────────────────────────────────
IMG_WIDTH=1080
IMG_HEIGHT=720

TARGET_BARCODE_WIDTH=1000
TARGET_BARCODE_HEIGHT=700

MAX_ROWS=90
MAX_COLS=30
MAX_EC_LEVEL=8
CHUNK_SIZE=10

ROWS=15
COLS=13
EC=5

OUTPUT_DIR="test-witness"
MOD=7237005577332262213973186563042994240857116359379907606001950938285454250989

# ── Sanity checks ─────────────────────────────────────────────────────────────
if ! python -c 'import sys; exit(0 if sys.prefix != sys.base_prefix else 1)'; then
    echo "Error: Not inside a virtual environment; exiting."
    echo "Please activate a virtual environment and try again."
    exit 1
fi
PYTHON_BIN=$(python -c 'import sys; print(sys.executable)')

mkdir -p "$OUTPUT_DIR"

BARCODE_FILE="$OUTPUT_DIR/barcode_r${ROWS}_c${COLS}_e${EC}_${IMG_WIDTH}x${IMG_HEIGHT}.png"
WITNESS_JSON="$OUTPUT_DIR/witness_r${ROWS}_c${COLS}_e${EC}_${IMG_WIDTH}x${IMG_HEIGHT}.json"
PARAMS_FILE="$OUTPUT_DIR/params.zok"

# ── Step 1: Generate barcode ──────────────────────────────────────────────────
echo "Step 1: Generating barcode..."
BARCODE_OUTPUT=$(${PYTHON_BIN} python-scripts/generate_barcode.py \
    -r "$ROWS" -c "$COLS" -e "$EC" \
    -o "$BARCODE_FILE" \
    --image-width "$IMG_WIDTH" --image-height "$IMG_HEIGHT" \
    --barcode-width "$TARGET_BARCODE_WIDTH" \
    --barcode-height "$TARGET_BARCODE_HEIGHT")
echo "$BARCODE_OUTPUT"
echo ""

# Extract real barcode dimensions and crop offset from generator output
REAL_BARCODE_W=$(echo "$BARCODE_OUTPUT" | sed -n 's/.*Rendered barcode size: \([0-9]*\)x.*/\1/p')
REAL_BARCODE_H=$(echo "$BARCODE_OUTPUT" | sed -n 's/.*Rendered barcode size: [0-9]*x\([0-9]*\) pixels/\1/p')
R_START=$(echo "$BARCODE_OUTPUT"        | sed -n 's/.*R_START=\([0-9]*\).*/\1/p')
C_START=$(echo "$BARCODE_OUTPUT"        | sed -n 's/.*C_START=\([0-9]*\).*/\1/p')

echo "Real barcode dimensions : ${REAL_BARCODE_W}x${REAL_BARCODE_H} pixels"
echo "Crop offset             : R_START=$R_START, C_START=$C_START"
echo "✓ Barcode generated: $BARCODE_FILE"
echo ""

# ── Step 2: Generate params.zok ───────────────────────────────────────────────
echo "Step 2: Generating params.zok..."
(
    cd external/rxing
    cargo run --release -p rxing-cli -- /dev/null generate-params \
        "../../$PARAMS_FILE" \
        --image-width    "$IMG_WIDTH" \
        --image-height   "$IMG_HEIGHT" \
        --barcode-width  "$REAL_BARCODE_W" \
        --barcode-height "$REAL_BARCODE_H" \
        --r-start        "$R_START" \
        --c-start        "$C_START" \
        --max-rows       "$MAX_ROWS" \
        --max-cols       "$MAX_COLS" \
        --max-ec-level   "$MAX_EC_LEVEL" \
        --chunk-size     "$CHUNK_SIZE"
)
echo "✓ params.zok written: $PARAMS_FILE"
echo ""

# ── Step 3: Decode barcode and generate witness JSON ──────────────────────────
echo "Step 3: Decoding barcode and generating witness JSON..."
(
    cd external/rxing
    cargo run --release -p rxing-cli -- "../../$BARCODE_FILE" decode \
        --barcode-types PDF_417 \
        --save-witness "../../$WITNESS_JSON" \
        --image-mode custom \
        --image-width    "$IMG_WIDTH" \
        --image-height   "$IMG_HEIGHT" \
        --barcode-width  "$REAL_BARCODE_W" \
        --barcode-height "$REAL_BARCODE_H" \
        --r-start        "$R_START" \
        --c-start        "$C_START" \
        --max-rows       "$MAX_ROWS" \
        --max-cols       "$MAX_COLS" \
        --max-ec-level   "$MAX_EC_LEVEL" \
        --chunk-size     "$CHUNK_SIZE"
)
echo "✓ Witness JSON written: $WITNESS_JSON"
echo ""

# ── Step 3b: Convert witness JSON to .pin and .vin ────────────────────────────
echo "Step 3b: Converting witness JSON to .pin and .vin..."
${PYTHON_BIN} python-scripts/json_to_witness.py \
    -i "$WITNESS_JSON" \
    --type bin_image=bool \
    --public wb_disjoint_set_poly_f \
    --public garbage_disjoint_set_poly_f \
    --modulus "$MOD" \
    --pin "${WITNESS_JSON%.json}.pin" \
    --vin "${WITNESS_JSON%.json}.vin"
echo "✓ Witness files written"
echo ""

ZOK_FILE="zokrates/for-measurement/bench_binarize.zok"
ZOK_FILE="$(cd "$(dirname "$ZOK_FILE")" && pwd)/$(basename "$ZOK_FILE")"
ZOK_BASENAME="bench_binarize"
WITNESS_PIN="$(pwd)/${WITNESS_JSON%.json}.pin"
WITNESS_VIN="$(pwd)/${WITNESS_JSON%.json}.vin"

if command -v gtime &>/dev/null; then
    gnu-time() { gtime --verbose "$@"; }
else
    gnu-time() { /usr/bin/time --verbose "$@"; }
fi

export RSMT2_CVC4_CMD=cvc5

# ── Step 4: Compile circuit and run trusted setup ─────────────────────────────
echo "Step 4: Compiling circuit and running trusted setup..."
(
    cd external/circ
    ./driver.py -F zok zokc r1cs spartan bellman smt
    ./driver.py -b
    ./target/release/examples/circ "$ZOK_FILE" --language zsharp-curly r1cs \
        --action setup \
        --proof-impl dorian \
        --pfcurve curve25519 \
        --prover-key  "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_P" \
        --verifier-key "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_V" \
        --pp           "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_PP"
)
echo "✓ Setup complete"
echo ""

# ── Step 5: Prove and verify ──────────────────────────────────────────────────
echo "Step 5: Generating proof..."
(
    cd external/circ
    gnu-time ./target/release/examples/zk_commit --action prove \
        --prover-key  "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_P" \
        --pp           "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_PP" \
        --inputs      "$WITNESS_PIN" \
        --proof        "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}.pi"
)
echo "✓ Proof generated"
echo ""

echo "Step 5 (verify): Verifying proof..."
(
    cd external/circ
    gnu-time ./target/release/examples/zk_commit --action verify \
        --verifier-key "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_V" \
        --pp           "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_PP" \
        --inputs      "$WITNESS_VIN" \
        --proof        "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}.pi"
)
echo "✓ Proof verified"
echo ""

echo "========================================"
echo "✓ Benchmark complete"
echo "========================================"
echo "Files in $OUTPUT_DIR/:"
ls -lh "$OUTPUT_DIR/"
