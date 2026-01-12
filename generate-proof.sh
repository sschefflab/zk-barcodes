#!/bin/bash

WITNESS_JSON="$1"
ZOK_FILE="$2"

# Extract the basename without extension for output files
ZOK_BASENAME=$(basename "$ZOK_FILE" .zok)

MOD=7237005577332262213973186563042994240857116359379907606001950938285454250989

python-scripts/venv/bin/python python-scripts/json_to_witness.py -i "$WITNESS_JSON" --map bin_image=binarized_image --map image=image --type bin_image=bool \
			       --modulus "$MOD" \
			       --pin "zokrates/bin/$ZOK_BASENAME.pin" --vin "zokrates/bin/$ZOK_BASENAME.vin"

export RSMT2_CVC4_CMD=cvc5

cd external/circ
./driver.py -F zok zokc r1cs spartan smt

./driver.py -b

./target/release/examples/circ "../../$ZOK_FILE" --language zsharp-curly \
    --field-custom-modulus "$MOD"  r1cs \
    --action spartan-setup \
    --prover-key "../../zokrates/bin/${ZOK_BASENAME}_P" \
    --verifier-key "../../zokrates/bin/${ZOK_BASENAME}_V" \

./target/release/examples/zk --prover-key ../../zokrates/bin/binarize_P --verifier-key ../../zokrates/bin/binarize_V \
	--pin ../../zokrates/bin/binarize.pin --vin ../../zokrates/bin/binarize.vin --action spartan

