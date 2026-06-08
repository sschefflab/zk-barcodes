#!/usr/bin/env bash
set -euo pipefail

# Find gnutime across platforms
if command -v gtime &>/dev/null; then
    gnu-time() { gtime --verbose "$@"; }
else
    gnu-time() { /usr/bin/time --verbose "$@"; }
fi

ITERATIONS=5
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_WITNESS_DIR="$SCRIPT_DIR/../test-witness"

mapfile -t IMAGES < <(find "$TEST_WITNESS_DIR" -maxdepth 1 -name "*.png" | sort)

if [[ ${#IMAGES[@]} -eq 0 ]]; then
    echo "No *.png files found in $TEST_WITNESS_DIR"
    exit 1
fi

echo "Found ${#IMAGES[@]} image(s) in $TEST_WITNESS_DIR, running $ITERATIONS iteration(s) each"

for IMAGE in "${IMAGES[@]}"; do
    IMAGE_BASENAME="$(basename "$IMAGE" | sed 's/\.[^.]*$//')"
    LOG_FILE="$SCRIPT_DIR/proof-runs/prove-output-${IMAGE_BASENAME}-$(date +%Y%m%d-%H%M%S).log"

    echo "=== Image: $IMAGE ==="
    echo "Output log: $LOG_FILE"

    for i in $(seq 1 "$ITERATIONS"); do
        echo "--- Iteration $i of $ITERATIONS ---" >> "$LOG_FILE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting iteration $i" | tee -a "$LOG_FILE"

        (cd "$SCRIPT_DIR/script" && RUST_LOG=info gnu-time cargo run --release -- --prove --image "$IMAGE") \
            2>&1 | tee -a "$LOG_FILE"

        if [[ "$(uname)" == "Darwin" ]]; then
            PROOF_SIZE=$(stat -f%z "$SCRIPT_DIR/script/proof.bin" 2>/dev/null || echo "proof.bin not found")
        else
            PROOF_SIZE=$(stat -c%s "$SCRIPT_DIR/script/proof.bin" 2>/dev/null || echo "proof.bin not found")
        fi
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iteration $i complete | proof.bin size: ${PROOF_SIZE} bytes" | tee -a "$LOG_FILE"
    done

    rm -f "$SCRIPT_DIR/script/proof.bin"
    echo "Done. Full output written to: $LOG_FILE"
done
