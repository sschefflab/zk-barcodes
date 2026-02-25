#!/bin/bash

ZOKRATES_DIR="zokrates"

# Usage: ./generate-r1cs.sh [ZOKRATES_DIR/zokrates_file.zok]
# If no file is specified, defaults to ZOKRATES_DIR/main.zok

# Get the input file from argument or default to main.zok
INPUT_FILE="${1:-${ZOKRATES_DIR}/main.zok}"

# Check if the input file exists, error if not
if [ ! -f "${ZOKRATES_DIR}/${INPUT_FILE}" ]; then
    echo "Error: Input file '${ZOKRATES_DIR}/${INPUT_FILE}' not found"
    exit 1
fi

# Extract the basename without extension for output files
BASENAME=$(basename "$INPUT_FILE" .zok)

mkdir -p "${ZOKRATES_DIR}/bin"

export RSMT2_CVC4_CMD=cvc5

cd external/circ
./driver.py -F zok zokc r1cs spartan smt bellman

./driver.py -b

./target/release/examples/circ "../../${ZOKRATES_DIR}/${INPUT_FILE}" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl dorian \
    --prover-key "../../${ZOKRATES_DIR}/bin/${BASENAME}_P" \
    --verifier-key "../../${ZOKRATES_DIR}/bin/${BASENAME}_V" \

# ./target/release/examples/r1cs_inspect "../../${ZOKRATES_DIR}/bin/${BASENAME}_P" > "../../${ZOKRATES_DIR}/bin/${BASENAME}_r1cs"

# This maybe goes on setup if we ever go back to spartan:
 #    --field-custom-modulus 7237005577332262213973186563042994240857116359379907606001950938285454250989 r1cs \

