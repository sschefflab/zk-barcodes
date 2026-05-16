#!/bin/bash

WITNESS_JSON="$1"
ZOK_FILE="$2"
COMMIT_INPUT=""

# Parse optional flags
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --commit-input) COMMIT_INPUT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; TO_EXIT=1; shift ;;
    esac
done

ZOKRATES_DIR="zokrates"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find gnutime across platforms
if command -v gtime &>/dev/null; then
    gnu-time() { gtime --verbose "$@"; }
else
    gnu-time() { /usr/bin/time --verbose "$@"; }
fi

# Handle input errors + provide usage
TO_EXIT=0
# Check if arguments are provided
if [ -z "$WITNESS_JSON" ] || [ -z "$ZOK_FILE" ]; then
    echo "Error: Missing required arguments"
    TO_EXIT=1
fi
# Check if $1 is a .json file
if [[ ! "$WITNESS_JSON" =~ \.json$ ]]; then
    echo "Error: First argument must be a .json file, got: $WITNESS_JSON"
    TO_EXIT=1
fi
# Check if $2 is a .zok file
if [[ ! "$ZOK_FILE" =~ \.zok$ ]]; then
    echo "Error: Second argument must be a .zok file, got: $ZOK_FILE"
    TO_EXIT=1
fi

# Resolve ZOK_FILE to absolute path
ZOK_FILE="$(cd "$(dirname "$ZOK_FILE")" && pwd)/$(basename "$ZOK_FILE")"

# Check if ZoKrates file exists
if [ ! -f "${ZOK_FILE}" ]; then
    echo "Error: ZoKrates file not found: ${ZOK_FILE}"
    TO_EXIT=1
fi
# Derive .pin and .vin paths from witness JSON (same directory, same basename)
WITNESS_BASE="$(cd "$(dirname "$WITNESS_JSON")" && pwd)/$(basename "$WITNESS_JSON" .json)"
WITNESS_PIN="${WITNESS_BASE}.pin"
WITNESS_VIN="${WITNESS_BASE}.vin"

# Check if witness files exist
if [ ! -f "${WITNESS_JSON}" ]; then
    echo "Error: Witness file not found: ${WITNESS_JSON}"
    TO_EXIT=1
fi
if [ ! -f "${WITNESS_PIN}" ]; then
    echo "Error: Witness .pin file not found: ${WITNESS_PIN}"
    TO_EXIT=1
fi
if [ ! -f "${WITNESS_VIN}" ]; then
    echo "Error: Witness .vin file not found: ${WITNESS_VIN}"
    TO_EXIT=1
fi
# Print usage and exit if there were any errors
if [ $TO_EXIT -eq 1 ]; then
    echo "Usage: $0 <witness.json> </path/to/file.zok> [--commit-input <input_name>]"
    echo "Example: $0 test-witness/w.json zokrates/main.zok --commit-input image"
    exit 1
fi



# Extract the basename without extension for output files
ZOK_BASENAME=$(basename "$ZOK_FILE" .zok)

export RSMT2_CVC4_CMD=cvc5

cd "${SCRIPT_DIR}/external/circ"
./driver.py -F zok zokc r1cs spartan bellman smt

./driver.py -b

COMMIT_FLAG=""
[ -n "$COMMIT_INPUT" ] && COMMIT_FLAG="--r1cs-commit-input $COMMIT_INPUT"

./target/release/examples/circ "${ZOK_FILE}" --language zsharp-curly $COMMIT_FLAG r1cs \
    --action setup \
    --proof-impl dorian \
    --pfcurve curve25519 \
    --prover-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --verifier-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V" \
    --pp "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_PP"

gnu-time ./target/release/examples/zk_commit --action prove $COMMIT_FLAG \
    --prover-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --pp "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_PP" \
    --inputs "${WITNESS_PIN}" \
    --proof "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"

gnu-time ./target/release/examples/zk_commit --action verify $COMMIT_FLAG \
    --verifier-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V" \
    --pp "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_PP" \
    --inputs "${WITNESS_VIN}" \
    --proof "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"
