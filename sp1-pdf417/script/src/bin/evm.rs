//! Generate an EVM-compatible proof for on-chain verification.
//!
//! A "fixture" is a static JSON file containing a pre-generated proof, its public values,
//! and the verification key. It is used to test on-chain Solidity verifier contracts so
//! that tests can verify a real proof without re-generating one each run. Only needed if
//! you plan to verify proofs in a Solidity contract (e.g. with Foundry tests).
//!
//! ```shell
//! RUST_LOG=info cargo run --release --bin evm -- --system groth16 --image path/to/barcode.png
//! RUST_LOG=info cargo run --release --bin evm -- --system plonk   --image path/to/barcode.png
//! ```

use alloy_sol_types::SolType;
use clap::{Parser, ValueEnum};
use pdf417_lib::PublicValuesStruct;
use serde::{Deserialize, Serialize};
use sp1_sdk::{
    blocking::{ProveRequest, Prover, ProverClient},
    include_elf, Elf, HashableKey, ProvingKey, SP1ProofWithPublicValues, SP1Stdin, SP1VerifyingKey,
};
use std::path::PathBuf;

const PDF417_ELF: Elf = include_elf!("pdf417-program");

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct EVMArgs {
    #[arg(long)]
    image: String,

    #[arg(long, value_enum, default_value = "groth16")]
    system: ProofSystem,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum ProofSystem {
    Plonk,
    Groth16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SP1PDF417ProofFixture {
    barcode_text: String,
    vkey: String,
    public_values: String,
    proof: String,
}

fn main() {
    sp1_sdk::utils::setup_logger();

    let args = EVMArgs::parse();
    let client = ProverClient::from_env();
    let pk = client.setup(PDF417_ELF).expect("failed to setup elf");

    let image_bytes = std::fs::read(&args.image)
        .unwrap_or_else(|e| panic!("failed to read image '{}': {}", args.image, e));

    let mut stdin = SP1Stdin::new();
    stdin.write_vec(image_bytes);

    println!("Proof System: {:?}", args.system);

    let proof = match args.system {
        ProofSystem::Plonk => client.prove(&pk, stdin).plonk().run(),
        ProofSystem::Groth16 => client.prove(&pk, stdin).groth16().run(),
    }
    .expect("failed to generate proof");

    create_proof_fixture(&proof, pk.verifying_key(), args.system);
}

fn create_proof_fixture(
    proof: &SP1ProofWithPublicValues,
    vk: &SP1VerifyingKey,
    system: ProofSystem,
) {
    let bytes = proof.public_values.as_slice();
    let decoded = PublicValuesStruct::abi_decode(bytes).unwrap();
    let barcode_text = String::from_utf8(decoded.barcode_text.to_vec())
        .expect("barcode text is not valid UTF-8");

    let fixture = SP1PDF417ProofFixture {
        barcode_text,
        vkey: vk.bytes32().to_string(),
        public_values: format!("0x{}", hex::encode(bytes)),
        proof: format!("0x{}", hex::encode(proof.bytes())),
    };

    println!("Verification Key: {}", fixture.vkey);
    println!("Public Values: {}", fixture.public_values);
    println!("Proof Bytes: {}", fixture.proof);

    // Write the fixture to disk for use in Solidity/Foundry tests.
    let fixture_path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../contracts/src/fixtures");
    std::fs::create_dir_all(&fixture_path).expect("failed to create fixture path");
    std::fs::write(
        fixture_path.join(format!("{:?}-fixture.json", system).to_lowercase()),
        serde_json::to_string_pretty(&fixture).unwrap(),
    )
    .expect("failed to write fixture");
}
