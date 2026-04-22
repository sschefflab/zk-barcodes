#!/bin/bash

WITNESS_JSON="$1"
ZOK_FILE="$2"

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
    echo "Usage: $0 <witness.json> </path/to/file.zok>"
    exit 1
fi



# Extract the basename without extension for output files
ZOK_BASENAME=$(basename "$ZOK_FILE" .zok)

export RSMT2_CVC4_CMD=cvc5

cd "${SCRIPT_DIR}/external/circ"
./driver.py -F zok zokc r1cs bellman smt

./driver.py -b

./target/release/examples/circ "${ZOK_FILE}" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl dorian \
    --prover-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --verifier-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V"

gnu-time ./target/release/examples/zk --action prove \
    --proof-impl dorian \
    --prover-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --inputs "${WITNESS_PIN}" \
    --proof "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"

gnu-time ./target/release/examples/zk --action verify \
    --proof-impl dorian \
    --verifier-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V" \
    --inputs "${WITNESS_VIN}" \
    --proof "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"
