# rxing - Rust Barcode library

A pure Rust port of the ZXing Java barcode library.

## Project Overview

- **Purpose:** Provide a complete, hand-ported Rust implementation of the ZXing barcode scanning and generation library.
- **Main Technologies:** Rust (2021 edition), `image`, `imageproc`, `clap` (for CLI), `serde` (optional).
- **Architecture:** 
    - The main logic resides in the root crate `rxing`.
    - `src/` contains the core library, including readers and writers for various barcode formats (Aztec, QR Code, Data Matrix, PDF417, etc.).
    - `src/common/` contains shared utilities like Reed-Solomon error correction, BitMatrix, and BitArray.
    - `src/oned/` contains 1D barcode logic.
    - `src/helpers.rs` provides a high-level API for common tasks like detecting barcodes in files or images.
    - `crates/cli` contains a command-line tool for decoding and encoding barcodes.
    - `crates/one-d-proc-derive` contains procedural macros for 1D readers.

## Building and Running

### Prerequisites
- Rust 1.85 or higher.

### Key Commands
- **Build the library:** `cargo build`
- **Run all tests:** `cargo test`
- **Run specific tests (e.g., 1D):** `cargo test oned`
- **Build the CLI tool:** `cargo build -p rxing-cli`
- **Run the CLI tool (Decode example):** `cargo run -p rxing-cli -- <IMAGE_PATH> decode`
- **Run the CLI tool (Encode example):** `cargo run -p rxing-cli -- <OUTPUT_PATH> encode <FORMAT> --data <DATA>`
- **Run benchmarks:** `cargo bench`

### Feature Flags
The library uses several features to control dependencies:
- `image` (default): Enable image manipulation support.
- `client_support` (default): Parsing barcode results into common formats.
- `serde`: Serialization support.
- `svg_read`/`svg_write`: SVG support.

## Development Conventions

- **Rustification:** The project is an ongoing effort to "rustify" the original Java-like structure. Prefer idiomatic Rust patterns (e.g., Result, Option, generics).
- **Const Generics:** Recently updated to use const generics in 1D reader utilities for better performance and type safety.
- **Testing:** New features should include unit tests. Integration tests are located in `tests/`. Positive tests from ZXing are mostly implemented; negative tests are a work in progress.
- **Errors:** Uses a custom `Exceptions` enum for error handling.
- **Formatting:** Standard Rust formatting (rustfmt).
- **Safety:** Strives for safe Rust; thread-safety was improved in v0.6.0 by moving away from `Rc` and `Arc` where possible.
