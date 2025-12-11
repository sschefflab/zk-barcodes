#!/bin/bash

mkdir -p zokrates/bin

export RSMT2_CVC4_CMD=cvc5

cd external/circ
./driver.py -F zok zokc r1cs spartan smt

./driver.py -b

cd ../..
./external/circ/target/release/examples/circ zokrates/main.zok --language zsharp-curly r1cs \
    --action spartan-setup \
    --prover-key zokrates/bin/P \
    --verifier-key zokrates/bin/V

./external/circ/target/release/examples/r1cs_inspect zokrates/bin/P > zokrates/bin/r1cs


