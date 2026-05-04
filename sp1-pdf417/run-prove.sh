#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 --image <path> --iterations <n>"
    exit 1
}

IMAGE=""
ITERATIONS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image) IMAGE="$2"; shift 2 ;;
        --iterations) ITERATIONS="$2"; shift 2 ;;
        *) usage ;;
    esac
done

[[ -z "$IMAGE" || -z "$ITERATIONS" ]] && usage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_BASENAME="$(basename "$IMAGE" | sed 's/\.[^.]*$//')"
LOG_FILE="$SCRIPT_DIR/prove-output-${IMAGE_BASENAME}-$(date +%Y%m%d-%H%M%S).log"

echo "Running $ITERATIONS prove iteration(s) for image: $IMAGE"
echo "Output log: $LOG_FILE"

for i in $(seq 1 "$ITERATIONS"); do
    echo "--- Iteration $i of $ITERATIONS ---" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting iteration $i" | tee -a "$LOG_FILE"

    (cd "$SCRIPT_DIR/script" && RUST_LOG=info cargo run --release -- --prove --image "$IMAGE") \
        2>&1 | tee -a "$LOG_FILE"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iteration $i complete" | tee -a "$LOG_FILE"
done

echo "Done. Full output written to: $LOG_FILE"
