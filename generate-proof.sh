#!/bin/bash

WITNESS_JSON="$1"
ZOK_FILE="$2"

ZOKRATES_DIR="zokrates"

# Handle input errors + provide usage
TO_EXIT=0
# Check if arguments are provided
if [ -z "$WITNESS_JSON" ] || [ -z "$ZOK_FILE" ]; then
    echo "Error: Missing required arguments"
    TO_EXIT=1
fi
# Check if ZoKrates file exists in the zokrates directory
if [ ! -f "${ZOKRATES_DIR}/${ZOK_FILE}" ]; then
    echo "Error: ZoKrates file not found: ${ZOKRATES_DIR}/${ZOK_FILE}"
    TO_EXIT=1
fi
# Derive .pin and .vin paths from witness JSON (same directory, same basename)
WITNESS_BASE="${WITNESS_JSON%.json}"
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
# Print usage and exit if there were any errors
if [ $TO_EXIT -eq 1 ]; then
    echo "Usage: $0 <witness.json> <file.zok>"
    echo "<file.zok> should be in the ./zokrates/ directory (with no leading path)"
    exit 1
fi



# Extract the basename without extension for output files
ZOK_BASENAME=$(basename "$ZOK_FILE" .zok)

export RSMT2_CVC4_CMD=cvc5

cd external/circ
./driver.py -F zok zokc r1cs bellman smt

./driver.py -b

./target/release/examples/circ "../../${ZOKRATES_DIR}/${ZOK_FILE}" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl dorian \
    --prover-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --verifier-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V"

./target/release/examples/zk --action prove \
    --proof-impl dorian \
    --prover-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --inputs "../../${WITNESS_PIN}" \
    --proof "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"

./target/release/examples/zk --action verify \
    --proof-impl dorian \
    --verifier-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V" \
    --inputs "../../${WITNESS_VIN}" \
    --proof "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"
