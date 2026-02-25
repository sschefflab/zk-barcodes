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
# Check if witness file exists in the zokrates directory
if [ ! -f "${WITNESS_JSON}" ]; then
    echo "Error: Witness file not found: ${WITNESS_JSON}"
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

# The commented-out stuff is for use with Spartan. Spartan in basic circ does not implement lookups. Using mirage for now.

#MOD=7237005577332262213973186563042994240857116359379907606001950938285454250989
MOD=52435875175126190479447740508185965837690552500527637822603658699938581184513

# Get python path from within venv
# TODO: Write an opt-out flag that lets the user run not in a venv if they absolutely want to. For now, just assume they are using the venv and error if not.
if ! python -c 'import sys; exit(0 if sys.prefix != sys.base_prefix else 1)'; then
    echo "Not inside a virtual environment; exiting. Please activate a virtual environment and try again."
    exit 1
fi
PYTHON_BIN=$(python -c 'import sys; print(sys.executable)')

${PYTHON_BIN} python-scripts/json_to_witness.py -i "$WITNESS_JSON" --map bin_image=binarized_image --map image=image --type bin_image=bool \
			       --modulus "$MOD" \
			       --pin "${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pin" --vin "${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.vin"

export RSMT2_CVC4_CMD=cvc5

cd external/circ
#./driver.py -F zok zokc r1cs spartan smt
./driver.py -F zok zokc r1cs bellman smt

./driver.py -b

./target/release/examples/circ "../../${ZOKRATES_DIR}/${ZOK_FILE}" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl mirage \
    --prover-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --verifier-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V"

#    --field-custom-modulus "$MOD"  r1cs \
#    --action spartan-setup \

# ./target/release/examples/zk --prover-key ../../${ZOKRATES_DIR}/bin/binarize_P --verifier-key ../../${ZOKRATES_DIR}/bin/binarize_V \
# 	--pin ../../${ZOKRATES_DIR}/bin/binarize.pin --vin ../../${ZOKRATES_DIR}/bin/binarize.vin --action spartan

./target/release/examples/zk --action prove \
    --proof-impl mirage \
    --prover-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_P" \
    --inputs "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pin" \
    --proof "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"

./target/release/examples/zk --action verify \
    --proof-impl mirage \
    --verifier-key "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}_V" \
    --inputs "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.vin" \
    --proof "../../${ZOKRATES_DIR}/bin/${ZOK_BASENAME}.pi"
