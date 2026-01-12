#!/bin/bash

WITNESS_JSON="$1"
ZOK_FILE="$2"

# Extract the basename without extension for output files
ZOK_BASENAME=$(basename "$ZOK_FILE" .zok)

# The commented-out stuff is for use with Spartan. Spartan in basic circ does not implement lookups. Using mirage for now.

#MOD=7237005577332262213973186563042994240857116359379907606001950938285454250989
MOD=52435875175126190479447740508185965837690552500527637822603658699938581184513

python-scripts/venv/bin/python python-scripts/json_to_witness.py -i "$WITNESS_JSON" --map bin_image=binarized_image --map image=image --type bin_image=bool \
			       --modulus "$MOD" \
			       --pin "zokrates/bin/${ZOK_BASENAME}.pin" --vin "zokrates/bin/${ZOK_BASENAME}.vin"

export RSMT2_CVC4_CMD=cvc5

cd external/circ
#./driver.py -F zok zokc r1cs spartan smt
./driver.py -F zok zokc r1cs bellman smt

./driver.py -b

./target/release/examples/circ "../../$ZOK_FILE" --language zsharp-curly r1cs \
    --action setup \
    --proof-impl mirage \
    --prover-key "../../zokrates/bin/${ZOK_BASENAME}_P" \
    --verifier-key "../../zokrates/bin/${ZOK_BASENAME}_V"

#    --field-custom-modulus "$MOD"  r1cs \
#    --action spartan-setup \

# ./target/release/examples/zk --prover-key ../../zokrates/bin/binarize_P --verifier-key ../../zokrates/bin/binarize_V \
# 	--pin ../../zokrates/bin/binarize.pin --vin ../../zokrates/bin/binarize.vin --action spartan

./target/release/examples/zk --action prove \
    --proof-impl mirage \
    --prover-key "../../zokrates/bin/${ZOK_BASENAME}_P" \
    --inputs "../../zokrates/bin/${ZOK_BASENAME}.pin" \
    --proof "../../zokrates/bin/${ZOK_BASENAME}.pi"

./target/release/examples/zk --action verify \
    --proof-impl mirage \
    --verifier-key "../../zokrates/bin/${ZOK_BASENAME}_V" \
    --inputs "../../zokrates/bin/${ZOK_BASENAME}.vin" \
    --proof "../../zokrates/bin/${ZOK_BASENAME}.pi"
