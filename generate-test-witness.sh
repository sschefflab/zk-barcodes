#!/bin/bash

# Test witness generation script
# Generates a test barcode, decodes it, and creates witness files

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d, --dir DIR        Output directory (default: test-witness)"
    echo "  -r, --rows N         Barcode rows (default: 3)"
    echo "  -c, --cols N         Barcode columns (default: 2)"
    echo "  -e, --ec N           Error correction level (default: 1)"
    echo "  --max-rows N         Max rows passed to rxing decoder (default: same as --rows)"
    echo "  --max-cols N         Max cols passed to rxing decoder (default: same as --cols)"
    echo "  --max-ec N           Max EC level passed to rxing decoder (default: same as --ec)"
    echo "  --chunk-size N       Block chunk size in pixels passed to rxing decoder"
    echo "  -W, --image-width N      Canvas image width in pixels"
    echo "  -H, --image-height N     Canvas image height in pixels"
    echo "  --barcode-width N        Target barcode width in pixels within canvas (requires -W/-H)"
    echo "  --barcode-height N       Target barcode height in pixels within canvas (requires -W/-H)"
    echo "  -h, --help               Show this help"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 --rows 10 --cols 5 --ec 2"
    echo "  $0 --rows 15 --cols 8 --ec 2 --image-width 1080 --image-height 720 --barcode-width 900 --barcode-height 600"
    echo "  $0 -r 10 -c 5 -e 2 -W 1920 -H 1080 --barcode-width 1600 --barcode-height 900 -d my-witness"
}

# Defaults
WITNESS_DIR="test-witness"
ROWS=3
COLS=2
EC=1
MAX_ROWS=""
MAX_COLS=""
MAX_EC=""
CHUNK_SIZE=""
IMG_WIDTH=""
IMG_HEIGHT=""
BARCODE_WIDTH=""
BARCODE_HEIGHT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--dir)            WITNESS_DIR="$2";    shift 2 ;;
        -r|--rows)           ROWS="$2";           shift 2 ;;
        -c|--cols)           COLS="$2";           shift 2 ;;
        -e|--ec)             EC="$2";             shift 2 ;;
        --max-rows)          MAX_ROWS="$2";       shift 2 ;;
        --max-cols)          MAX_COLS="$2";       shift 2 ;;
        --max-ec)            MAX_EC="$2";         shift 2 ;;
        --chunk-size)        CHUNK_SIZE="$2";     shift 2 ;;
        -W|--image-width)    IMG_WIDTH="$2";      shift 2 ;;
        -H|--image-height)   IMG_HEIGHT="$2";     shift 2 ;;
        --barcode-width)     BARCODE_WIDTH="$2";  shift 2 ;;
        --barcode-height)    BARCODE_HEIGHT="$2"; shift 2 ;;
        -h|--help)           usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Validate that barcode dimensions require canvas dimensions
if { [ -n "$BARCODE_WIDTH" ] || [ -n "$BARCODE_HEIGHT" ]; } && { [ -z "$IMG_WIDTH" ] || [ -z "$IMG_HEIGHT" ]; }; then
    echo "Error: --barcode-width/--barcode-height require --image-width and --image-height"
    exit 1
fi

# Build filename suffix for image dimensions
IMG_SUFFIX=""
if [ -n "$IMG_WIDTH" ] && [ -n "$IMG_HEIGHT" ]; then
    IMG_SUFFIX="_${IMG_WIDTH}x${IMG_HEIGHT}"
elif [ -n "$IMG_WIDTH" ]; then
    IMG_SUFFIX="_w${IMG_WIDTH}"
elif [ -n "$IMG_HEIGHT" ]; then
    IMG_SUFFIX="_h${IMG_HEIGHT}"
fi

BARCODE_FILE="$WITNESS_DIR/pdf417_r${ROWS}_c${COLS}_e${EC}${IMG_SUFFIX}.png"
WITNESS_FILE="$WITNESS_DIR/witness_r${ROWS}_c${COLS}_e${EC}${IMG_SUFFIX}.json"
WITNESS_PIN="$WITNESS_DIR/witness_r${ROWS}_c${COLS}_e${EC}${IMG_SUFFIX}.pin"
WITNESS_VIN="$WITNESS_DIR/witness_r${ROWS}_c${COLS}_e${EC}${IMG_SUFFIX}.vin"

MOD=7237005577332262213973186563042994240857116359379907606001950938285454250989

echo "Test Witness Generation"
echo "======================"
echo "Parameters: ROWS=$ROWS, COLS=$COLS, EC=$EC, WITNESS_DIR=$WITNESS_DIR"
if [ -n "$IMG_WIDTH" ] || [ -n "$IMG_HEIGHT" ]; then
    echo "Image size: ${IMG_WIDTH:-auto}x${IMG_HEIGHT:-auto}"
fi
echo ""

# Check if inside virtual environment
if ! python -c 'import sys; exit(0 if sys.prefix != sys.base_prefix else 1)'; then
    echo "Error: Not inside a virtual environment; exiting."
    echo "Please activate a virtual environment and try again."
    exit 1
fi
PYTHON_BIN=$(python -c 'import sys; print(sys.executable)')

# Create/wipe witness directory
echo "Preparing $WITNESS_DIR directory..."
mkdir -p "$WITNESS_DIR"
echo "✓ Directory ready"
echo ""

# Step 1: Generate barcode
echo "Step 1: Generating barcode..."
BARCODE_ARGS="-r $ROWS -c $COLS -e $EC -o $BARCODE_FILE"
[ -n "$IMG_WIDTH" ]     && BARCODE_ARGS="$BARCODE_ARGS --image-width $IMG_WIDTH"
[ -n "$IMG_HEIGHT" ]    && BARCODE_ARGS="$BARCODE_ARGS --image-height $IMG_HEIGHT"
[ -n "$BARCODE_WIDTH" ] && BARCODE_ARGS="$BARCODE_ARGS --barcode-width $BARCODE_WIDTH"
[ -n "$BARCODE_HEIGHT" ] && BARCODE_ARGS="$BARCODE_ARGS --barcode-height $BARCODE_HEIGHT"
${PYTHON_BIN} python-scripts/generate_barcode.py $BARCODE_ARGS
if [ $? -ne 0 ]; then
    echo "Error: Failed to generate barcode"
    exit 1
fi
echo "✓ Barcode generated: $BARCODE_FILE"
echo ""

# Step 2: Decode barcode and generate witness
echo "Step 2: Decoding barcode and generating witness..."
cd external/rxing
RXING_MODE_ARG=""
if [ -n "$IMG_WIDTH" ] && [ -n "$IMG_HEIGHT" ]; then
    RXING_MODE_ARG="--image-mode custom --image-width $IMG_WIDTH --image-height $IMG_HEIGHT --max-rows ${MAX_ROWS:-$ROWS} --max-cols ${MAX_COLS:-$COLS} --max-ec-level ${MAX_EC:-$EC}"
    [ -n "$CHUNK_SIZE" ] && RXING_MODE_ARG="$RXING_MODE_ARG --chunk-size $CHUNK_SIZE"
    [ -n "$BARCODE_WIDTH" ]  && RXING_MODE_ARG="$RXING_MODE_ARG --barcode-width $BARCODE_WIDTH"
    [ -n "$BARCODE_HEIGHT" ] && RXING_MODE_ARG="$RXING_MODE_ARG --barcode-height $BARCODE_HEIGHT"
fi
cargo run --release -p rxing-cli -- "../../$BARCODE_FILE" decode --save-witness "../../$WITNESS_FILE" --barcode-types PDF_417 $RXING_MODE_ARG
if [ $? -ne 0 ]; then
    echo "Error: Failed to decode barcode"
    cd ../..
    exit 1
fi
cd ../..
echo "✓ Witness generated: $WITNESS_FILE"
echo ""

# Step 3: Convert witness JSON to witness files
# TODO: remove the words public values when done testing
echo "Step 3: Converting witness JSON to .pin and .vin files..."
${PYTHON_BIN} python-scripts/json_to_witness.py \
    -i "$WITNESS_FILE" \
    --type bin_image=bool \
    --public wb_disjoint_set_poly_f \
    --public garbage_disjoint_set_poly_f \
    --public wb_words \
    --public garbage_rows \
    --modulus "$MOD" \
    --pin "$WITNESS_PIN" \
    --vin "$WITNESS_VIN"
if [ $? -ne 0 ]; then
    echo "Error: Failed to convert witness JSON"
    exit 1
fi
echo "✓ Witness files generated:"
echo "  - $WITNESS_PIN"
echo "  - $WITNESS_VIN"
echo ""

echo "========================================"
echo "✓ Test witness generation complete!"
echo "========================================"
echo ""
echo "Generated files in $WITNESS_DIR/:"
ls -lh "$WITNESS_DIR/"
