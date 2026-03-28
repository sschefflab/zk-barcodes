# zkVM Proving for PDF417 barcode decoding

This is the SP1 template modified to read in an image file and then prove the decoding of those *private* image bytes as a PDF417 barcode into text.

## Quickstart usage
1. Generate your test image using the generate-barcode.py script in ../python-scripts
2. Move it into script/src/bin/test-images
3. From the script directory, run `RUST_LOG=info cargo run --release -- --execute --image test-images/<FILENAME>` to test that all is well and the zkVM will execute the program.
4. From the script directory, run `RUST_LOG=info cargo run --release -- --prove --image test-images/<FILENAME>` to prove, write out the proof to `proof.bin`, and check that the proof verifies.

## Project Structure

The lib directory contains the function that will be proved. It calls library `rxing` to do the decoding.

The program directory is what is actually run inside the zkVM and contains calls to the sp1 library to make this happen. To ensure the program is building, run:
```
cd program && cargo prove build
```
This will generate an ELF file, indicating the program successfully compiled to RISC-V.

The script directory contains code that is run on prove and verify. It does the image file read before starting the zkVM, and then it passes those bytes privately to the VM.

The `script/src/bin/main.rs` can be *executed* to confirm that the program will run on the VM and print the number of cycles. Then, it can be run with the prove flag to actually prove at each step. See commands below:

```
cd script
RUST_LOG=info cargo run --release -- --execute --image test-images/<FILENAME>
RUST_LOG=info cargo run --release -- --prove --image test-images/<FILENAME>
```
Proving also checks that the proof verifies successfully.

The vendor directory contains a copy of rxing, but with uses of chrono timing calls stubbed out. The library collects metadata about when decoding occurred. Timing calls are unimplemented on the SP1 VM and cause panics, and besides, we don't need this metadata. Our copy is the same as the public library, just with calls to chrono stubbed out with zeros.


## Initial instructions from SP1

This is a template for creating an end-to-end [SP1](https://github.com/succinctlabs/sp1) project
that can generate a proof of any RISC-V program.

### Requirements

- [Rust](https://rustup.rs/)
- [SP1](https://docs.succinct.xyz/docs/sp1/getting-started/install)

### Running the Project

There are 3 main ways to run this project: execute a program, generate a core proof, and
generate an EVM-compatible proof.

#### Build the Program

The program is automatically built through `script/build.rs` when the script is built.

#### Execute the Program

To run the program without generating a proof:

```sh
cd script
cargo run --release -- --execute
```

This will execute the program and display the output.

#### Generate an SP1 Core Proof

To generate an SP1 [core proof](https://docs.succinct.xyz/docs/next/sp1/generating-proofs/proof-types#core-default) for your program:

```sh
cd script
cargo run --release -- --prove
```

#### Generate an EVM-Compatible Proof

> [!WARNING]
> You will need at least 16GB RAM to generate a Groth16 or PLONK proof. View the [SP1 docs](https://docs.succinct.xyz/docs/next/sp1/getting-started/hardware-requirements#local-proving) for more information.

Generating a proof that is cheap to verify on the EVM (e.g. Groth16 or PLONK) is more intensive than generating a core proof.

To generate a Groth16 proof:

```sh
cd script
cargo run --release --bin evm -- --system groth16
```

To generate a PLONK proof:

```sh
cargo run --release --bin evm -- --system plonk
```

These commands will also generate fixtures that can be used to test the verification of SP1 proofs
inside Solidity.

#### Retrieve the Verification Key

To retrieve your `programVKey` for your on-chain contract, run the following command in `script`:

```sh
cargo run --release --bin vkey
```

### Using the Prover Network

We highly recommend using the Succinct Prover Network for any non-trivial programs or benchmarking purposes. For more information, see the [quickstart guide](https://docs.succinct.xyz/docs/next/sp1/prover-network/quickstart).

To get started, copy the example environment file:

```sh
cp .env.example .env
```

Then, set the `SP1_PROVER` environment variable to `network` and set the `NETWORK_PRIVATE_KEY`
environment variable to your whitelisted private key.

For example, to generate an EVM-compatible proof using the prover network, run the following
command:

```sh
SP1_PROVER=network NETWORK_PRIVATE_KEY=... cargo run --release --bin evm
```
