#!/bin/bash

# Usage: ./generate-r1cs.sh [zokrates_file.zok]
# If no file is specified, defaults to main.zok

# Get the input file from argument or default to main.zok
INPUT_FILE="${1:-main.zok}"

# Extract the basename without extension for output files
BASENAME=$(basename "$INPUT_FILE" .zok)

mkdir -p zokrates/bin

export RSMT2_CVC4_CMD=cvc5

cd external/circ
./driver.py -F zok zokc r1cs spartan smt bellman

./driver.py -b

./target/release/examples/circ "../../zokrates/$INPUT_FILE" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl dorian \
    --prover-key "../../zokrates/bin/${BASENAME}_P" \
    --verifier-key "../../zokrates/bin/${BASENAME}_V" \

# ./target/release/examples/r1cs_inspect "../../zokrates/bin/${BASENAME}_P" > "../../zokrates/bin/${BASENAME}_r1cs"

# This maybe goes on setup if we ever go back to spartan:
 #    --field-custom-modulus 7237005577332262213973186563042994240857116359379907606001950938285454250989 r1cs \

