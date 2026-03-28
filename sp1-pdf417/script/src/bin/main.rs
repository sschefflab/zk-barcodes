//! Prove that a private image file decodes to a specific PDF417 barcode text.
//!
//! ```shell
//! RUST_LOG=info cargo run --release -- --execute --image path/to/barcode.png
//! RUST_LOG=info cargo run --release -- --prove   --image path/to/barcode.png
//! ```

use alloy_sol_types::SolType;
use clap::Parser;
use pdf417_lib::PublicValuesStruct;
use sp1_sdk::{
    Elf, ProvingKey, SP1Stdin,
    blocking::{ProveRequest, Prover, ProverClient},
    include_elf,
};

const PDF417_ELF: Elf = include_elf!("pdf417-program");

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(long)]
    execute: bool,

    #[arg(long)]
    prove: bool,

    /// Path to the image file containing the PDF417 barcode.
    #[arg(long)]
    image: String,
}

fn main() {
    sp1_sdk::utils::setup_logger();
    dotenv::dotenv().ok();

    let args = Args::parse();

    if args.execute == args.prove {
        eprintln!("Error: You must specify either --execute or --prove");
        std::process::exit(1);
    }

    // Read the image bytes on the host.
    let image_bytes = std::fs::read(&args.image)
        .unwrap_or_else(|e| panic!("failed to read image '{}': {}", args.image, e));

    // Pass image bytes as private input to the zkVM.
    let mut stdin = SP1Stdin::new();
    stdin.write_vec(image_bytes);

    let client = ProverClient::from_env();

    if args.execute {
        let (output, report) = client.execute(PDF417_ELF, stdin).run().unwrap();
        println!("Program executed successfully.");

        let decoded = PublicValuesStruct::abi_decode(output.as_slice()).unwrap();
        let barcode_text = String::from_utf8(decoded.barcode_text.to_vec())
            .expect("barcode text is not valid UTF-8");
        println!("Barcode text: {}", barcode_text);
        println!("Number of cycles: {}", report.total_instruction_count());
    } else {
        let pk = client.setup(PDF417_ELF).expect("failed to setup elf");

        let proof = client
            .prove(&pk, stdin)
            .run()
            .expect("failed to generate proof");

        println!("Successfully generated proof!");
        proof.save("proof.bin").expect("failed to save proof");

        client
            .verify(&proof, pk.verifying_key(), None)
            .expect("failed to verify proof");
        println!("Successfully verified proof!");

        let barcode_text = String::from_utf8(
            PublicValuesStruct::abi_decode(proof.public_values.as_slice())
                .unwrap()
                .barcode_text
                .to_vec(),
        )
        .expect("barcode text is not valid UTF-8");
        println!("Proven barcode text: {}", barcode_text);
    }
}
