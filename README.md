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
