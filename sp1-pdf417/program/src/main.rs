#![no_main]
sp1_zkvm::entrypoint!(main);

use alloy_sol_types::SolType;
use pdf417_lib::{decode_barcode_from_bytes, PublicValuesStruct};

pub fn main() {
    // Read raw image bytes as a private input — not committed to the proof.
    let image_bytes = sp1_zkvm::io::read_vec();

    // Decode the barcode inside the zkVM. The proof attests that these
    // private image bytes decode to the committed barcode text.
    let barcode_text = decode_barcode_from_bytes(&image_bytes)
        .expect("failed to decode barcode");

    // Commit only the barcode text as the public output.
    let bytes = PublicValuesStruct::abi_encode(&PublicValuesStruct {
        barcode_text: barcode_text.into_bytes().into(),
    });
    sp1_zkvm::io::commit_slice(&bytes);
}
