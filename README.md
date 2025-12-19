# zk-barcodes

## Usage Notes

The generate_r1cs.sh script requires cvc5 to run. On Mac, install that with
```
brew install --cask cvc5/cvc5/cvc5
```

Then, the script can be used to generate constraints. To generate constraints for the main function, just run the script with no arguments. If you want to run it for a different file, provide the file as an argument.  No need to pass the full path - it assumes that circuit files will be in the zokrates/ directory.

So, for the whole circuit:
```
./generate-r1cs.sh
```

And for example, for just binarize.zok:
```
./generate-r1cs.sh binarize.zok
```

The script will create the zokrates/bin directory if it does not already exist. Inside, it will create P, V, and r1cs files. \*_P and \*_V are binary files used with Spartan to actually prove and verify. \*_r1cs is a human-readable file containing the R1CS system.
