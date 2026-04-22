#!/bin/bash

ZOKRATES_DIR="zokrates"

# Usage: ./generate-r1cs.sh [/path/to/zokrates_file.zok]
# If no file is specified, defaults to ZOKRATES_DIR/main.zok

# Get the script's directory so we can resolve paths relative to the repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get the input file from argument or default to main.zok
INPUT_FILE="${1:-${SCRIPT_DIR}/${ZOKRATES_DIR}/main.zok}"

# Resolve to absolute path
INPUT_FILE="$(cd "$(dirname "$INPUT_FILE")" && pwd)/$(basename "$INPUT_FILE")"

# Check if the input file exists, error if not
if [ ! -f "${INPUT_FILE}" ]; then
    echo "Error: Input file '${INPUT_FILE}' not found"
    exit 1
fi

# Extract the basename without extension for output files
BASENAME=$(basename "$INPUT_FILE" .zok)

mkdir -p "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin"

export RSMT2_CVC4_CMD=cvc5

cd "${SCRIPT_DIR}/external/circ"
./driver.py -F zok zokc r1cs spartan smt bellman

./driver.py -b

./target/release/examples/circ "${INPUT_FILE}" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl dorian \
    --prover-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${BASENAME}_P" \
    --verifier-key "${SCRIPT_DIR}/${ZOKRATES_DIR}/bin/${BASENAME}_V" \

# ./target/release/examples/r1cs_inspect "../../${ZOKRATES_DIR}/bin/${BASENAME}_P" > "../../${ZOKRATES_DIR}/bin/${BASENAME}_r1cs"

# This maybe goes on setup if we ever go back to spartan:
 #    --field-custom-modulus 7237005577332262213973186563042994240857116359379907606001950938285454250989 r1cs \

