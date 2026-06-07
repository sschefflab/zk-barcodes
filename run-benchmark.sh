#!/bin/bash

set -euo pipefail

# ── Dry-run mode (set DRY_RUN=1 to skip setup/prove/verify and skip writing output file) ──
DRY_RUN=${DRY_RUN:-0}

# ── Benchmark parameters (overridable via env vars) ───────────────────────────
IMG_WIDTH=${IMG_WIDTH:-1080}
IMG_HEIGHT=${IMG_HEIGHT:-720}

TARGET_BARCODE_WIDTH=${TARGET_BARCODE_WIDTH:-1000}
TARGET_BARCODE_HEIGHT=${TARGET_BARCODE_HEIGHT:-700}

MAX_ROWS=${MAX_ROWS:-90}
MAX_COLS=${MAX_COLS:-30}
MAX_EC_LEVEL=${MAX_EC_LEVEL:-8}
CHUNK_SIZE=${CHUNK_SIZE:-10}
NUM_ITERATIONS=${NUM_ITERATIONS:-5}

ROWS=${ROWS:-15}
COLS=${COLS:-13}
EC=${EC:-5}

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
mkdir -p zokrates/bin

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

# ── Compute chunk size ────────────────────────────────────────────────────────
CHUNK_SIZE=""
for f in 10 9 11 8 12 7 13 6 5 4 3 2; do
    if (( REAL_BARCODE_W % f == 0 )); then
        CHUNK_SIZE=$f
        break
    fi
done
if [[ -z "$CHUNK_SIZE" ]]; then
    echo "Error: No suitable chunk size found for REAL_BARCODE_W=${REAL_BARCODE_W} (tried 2-13, excluding 1)"
    exit 1
fi
echo "Chunk size              : $CHUNK_SIZE (factor of REAL_BARCODE_W=${REAL_BARCODE_W})"
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

# ── Circuits to benchmark ─────────────────────────────────────────────────────
# Set CIRCUIT=<name> env var to run a single circuit, otherwise runs all below.
if [[ -n "${CIRCUIT:-}" ]]; then
    CIRCUITS=("$CIRCUIT")
else
    CIRCUITS=(
        # bench_binarize
        # bench_block_measurement
        bench_words_pipeline
        bench_check_barcode_stats
        bench_check_error_correction
        bench_check_num_cw
        bench_codewords_to_chars
        # bench_full_circuit
    )
fi

WITNESS_PIN="$(pwd)/${WITNESS_JSON%.json}.pin"
WITNESS_VIN="$(pwd)/${WITNESS_JSON%.json}.vin"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

if command -v gtime &>/dev/null; then
    gnu-time() { gtime --verbose "$@"; }
else
    gnu-time() { /usr/bin/time --verbose "$@"; }
fi

export RSMT2_CVC4_CMD=cvc5

if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry run] Circuits: ${CIRCUITS[*]}"
    echo "[dry run] Skipping setup, prove, and verify."
    echo "[dry run] Config: image=${IMG_WIDTH}x${IMG_HEIGHT} max_rows=${MAX_ROWS} max_cols=${MAX_COLS} max_ec=${MAX_EC_LEVEL}"
    exit 0
fi

# Tag that namespaces key files per sweep combination so sequential sweep runs don't overwrite each other.
KEY_TAG="${IMG_WIDTH}x${IMG_HEIGHT}_r${MAX_ROWS}c${MAX_COLS}e${MAX_EC_LEVEL}"

# ── Step 4a: Build CirC once ──────────────────────────────────────────────────
echo "Step 4: Building CirC..."
(
    cd external/circ
    ./driver.py -F zok zokc r1cs spartan bellman smt
    ./driver.py -b
)
echo "✓ CirC build complete"
echo ""

# ── Step 4b: Run trusted setup for all circuits in parallel ───────────────────
# Use parallel indexed arrays (bash 3 compatible — no declare -A).
echo "Step 4 (setup): Launching parallel trusted setup for all circuits..."
SETUP_NAMES=()
SETUP_PIDS=()
SETUP_LOGS=()
SETUP_COMMIT_FLAGS=()
for ZOK_BASENAME in "${CIRCUITS[@]}"; do
    ZOK_FILE="$(cd zokrates/for-measurement && pwd)/${ZOK_BASENAME}.zok"
    SETUP_LOG=$(mktemp)
    SETUP_NAMES+=("$ZOK_BASENAME")
    SETUP_LOGS+=("$SETUP_LOG")
    case "$ZOK_BASENAME" in
        bench_binarize|bench_full_circuit) COMMIT_FLAG="--r1cs-commit-input image" ;;
        *) COMMIT_FLAG="" ;;
    esac
    SETUP_COMMIT_FLAGS+=("$COMMIT_FLAG")
    (
        cd external/circ
        ./target/release/examples/circ "$ZOK_FILE" --language zsharp-curly $COMMIT_FLAG r1cs \
            --action setup \
            --proof-impl dorian \
            --pfcurve curve25519 \
            --prover-key  "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_P" \
            --verifier-key "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_V" \
            --pp           "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_PP"
    ) >"$SETUP_LOG" 2>&1 &
    SETUP_PIDS+=($!)
    echo "  Launched setup for $ZOK_BASENAME (pid $!)"
done

echo "  Waiting for all setups to finish..."
SETUP_FAILED=0
for idx in "${!SETUP_NAMES[@]}"; do
    if wait "${SETUP_PIDS[$idx]}"; then
        echo "  ✓ Setup done: ${SETUP_NAMES[$idx]}"
    else
        echo "  ✗ Setup FAILED: ${SETUP_NAMES[$idx]}"
        SETUP_FAILED=1
    fi
done

if [[ "$SETUP_FAILED" == "1" ]]; then
    echo "One or more setups failed. Logs:"
    for idx in "${!SETUP_NAMES[@]}"; do
        echo "--- ${SETUP_NAMES[$idx]} ---"
        cat "${SETUP_LOGS[$idx]}"
    done
    rm -f "${SETUP_LOGS[@]}"
    exit 1
fi
echo "✓ All setups complete"
echo ""

# ── Step 5: Per-circuit prove and verify ──────────────────────────────────────
for idx in "${!CIRCUITS[@]}"; do
    ZOK_BASENAME="${CIRCUITS[$idx]}"
    ZOK_FILE="$(cd zokrates/for-measurement && pwd)/${ZOK_BASENAME}.zok"
    MEASUREMENT_DIR="zokrates/for-measurement/measurements/${ZOK_BASENAME}"
    mkdir -p "$MEASUREMENT_DIR"
    MEASUREMENT_FILE="$MEASUREMENT_DIR/${TIMESTAMP}.txt"

    echo "========================================"
    echo "Circuit: $ZOK_BASENAME"
    echo "========================================"

    CIRCUIT_COMMIT_FLAG="${SETUP_COMMIT_FLAGS[$idx]}"
    COMMIT_INPUT_VALUE=$(echo "$CIRCUIT_COMMIT_FLAG" | grep -oP '(?<=--r1cs-commit-input )\S+' || echo "none")

    # Write params header and setup log to measurement file
    {
        echo "host:             $(hostname)"
        echo "timestamp:        $TIMESTAMP"
        echo "image:            ${IMG_WIDTH}x${IMG_HEIGHT}"
        echo "barcode_target:   ${TARGET_BARCODE_WIDTH}x${TARGET_BARCODE_HEIGHT}"
        echo "barcode_actual:   ${REAL_BARCODE_W}x${REAL_BARCODE_H}"
        echo "r_start:          $R_START"
        echo "c_start:          $C_START"
        echo "rows:             $ROWS"
        echo "cols:             $COLS"
        echo "ec:               $EC"
        echo "max_rows:         $MAX_ROWS"
        echo "max_cols:         $MAX_COLS"
        echo "max_ec_level:     $MAX_EC_LEVEL"
        echo "chunk_size:       $CHUNK_SIZE"
        echo "circuit:          $ZOK_BASENAME"
        echo "commit_input:     $COMMIT_INPUT_VALUE"
        echo "num_iterations:   $NUM_ITERATIONS"
        echo "---"
        echo "=== setup ==="
        cat "${SETUP_LOGS[$idx]}"
    } > "$MEASUREMENT_FILE"
    rm -f "${SETUP_LOGS[$idx]}"

    # ── Prove and verify (repeated NUM_ITERATIONS times) ─────────────────────
    for i in $(seq 1 "$NUM_ITERATIONS"); do
        echo "Step 5 (iteration $i/$NUM_ITERATIONS): Generating proof..."
        echo "=== prove iteration $i ===" >> "$MEASUREMENT_FILE"
        (
            cd external/circ
            gnu-time ./target/release/examples/zk_commit --action prove \
                $CIRCUIT_COMMIT_FLAG \
                --prover-key  "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_P" \
                --pp           "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_PP" \
                --inputs      "$WITNESS_PIN" \
                --proof        "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}.pi"
        ) 2>&1 | tee -a "$MEASUREMENT_FILE"
        echo "✓ Proof generated"
        echo ""

        echo "Step 5 (iteration $i/$NUM_ITERATIONS, verify): Verifying proof..."
        echo "=== verify iteration $i ===" >> "$MEASUREMENT_FILE"
        (
            cd external/circ
            gnu-time ./target/release/examples/zk_commit --action verify \
                $CIRCUIT_COMMIT_FLAG \
                --verifier-key "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_V" \
                --pp           "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}_PP" \
                --inputs      "$WITNESS_VIN" \
                --proof        "$(pwd)/../../zokrates/bin/${ZOK_BASENAME}_${KEY_TAG}.pi"
        ) 2>&1 | tee -a "$MEASUREMENT_FILE"
        echo "✓ Proof verified"
        echo ""
    done

    echo "✓ Circuit complete — results in $MEASUREMENT_FILE"
    echo ""
done

echo "========================================"
echo "✓ Benchmark complete"
echo "========================================"
echo "Files in $OUTPUT_DIR/:"
ls -lh "$OUTPUT_DIR/"
