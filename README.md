# zk-barcodes

## Requirements

The generate_r1cs.sh script requires the following packages to run:
- `cvc5`
- `libssl-dev` (openssl on MacOS, usually already installed)

On Mac:
```
brew install --cask cvc5/cvc5/cvc5
```

On Ubuntu:
```
apt-get install cvc5 libssl-dev
```

## Running test witness
Install all requirements, then run:
```
./generate-test-witness.sh
./generate-proof.sh test-witness/r3_c2_e1.json binarize.zok
```
Running generate-test-witness.sh should create a directory test-witness containing an example barcode, `test-witness/pdf417_r3_c2_e1.png` and the corresponding witness `witness_r3_c2_e1.json` and corresponding `.pin` and `.vin` files needed to run the proof.  Then, run `generate-proof.sh` on those files to generate a proof from that witness.

NOTE: When we are out of testing, `binarize.zok` should be `main.zok`

## Usage Notes

The script can be used to generate constraints. To generate constraints for the main function, just run the script with no arguments. If you want to run it for a different file, provide the file as an argument.  No need to pass the full path - it assumes that circuit files will be in the zokrates/ directory.

So, for the whole circuit:
```
./generate-r1cs.sh
```

And for example, for just binarize.zok:
```
./generate-r1cs.sh binarize.zok
```

The script will create the zokrates/bin directory if it does not already exist. Inside, it will create P, V, and r1cs files. \*_P and \*_V are binary files used with Spartan to actually prove and verify. \*_r1cs is a human-readable file containing the R1CS system.
