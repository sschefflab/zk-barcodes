use alloy_sol_types::sol;
use image;
use rxing::BarcodeFormat;

sol! {
    /// The public values committed by the zkVM program.
    struct PublicValuesStruct {
        bytes barcode_text;
    }
}

/// Decode a PDF417 barcode from raw image bytes.
///
/// This runs inside the zkVM, proving that the given private image bytes
/// decode to the committed barcode text.
pub fn decode_barcode_from_bytes(image_bytes: &[u8]) -> Result<String, String> {
    let img = image::load_from_memory(image_bytes)
        .map_err(|e| format!("image load error: {:?}", e))?;

    let luma = img.to_luma8();
    let (width, height) = luma.dimensions();
    let luma_data = luma.into_raw();

    rxing::helpers::detect_in_luma(luma_data, width, height, Some(BarcodeFormat::PDF_417))
        .map(|r| r.getText().to_owned())
        .map_err(|e| format!("{:?}", e))
}
