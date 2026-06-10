#!/bin/bash

# generate_witness_from_image.sh
# Accepts either an existing PDF417 barcode image OR barcode structure params to generate one,
# then produces:
#   - witness JSON (.json)
#   - witness input files (.pin, .vin)
#   - params.zok (ZoKrates parameter file)

set -euo pipefail

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Input — pick one:"
    echo "  -i, --image FILE       Use an existing PDF417 barcode image"
    echo "  -r, --rows N           Generate a barcode with this many rows (requires --cols, --ec)"
    echo "  -c, --cols N           Number of data columns for generated barcode"
    echo "  -e, --ec N             Error correction level 0-8 for generated barcode"
    echo ""
    echo "Output:"
    echo "  -d, --dir DIR          Output directory (default: witness-out)"
    echo "  -p, --params FILE      Output path for params.zok (default: DIR/params.zok)"
    echo ""
    echo "Image dimensions:"
    echo "  -W, --width N          Image width in pixels"
    echo "  -H, --height N         Image height in pixels"
    echo "  (omit both)            Auto-read from image file via Pillow (existing image only)"
    echo ""
    echo "Barcode structure hints (for params.zok):"
    echo "  --max-rows N           Maximum PDF417 rows (default: 90, or actual rows when generating)"
    echo "  --max-cols N           Maximum PDF417 data columns (default: 30, or actual cols when generating)"
    echo "  --max-ec-level N       Maximum error correction level 0-8 (default: 8, or actual EC when generating)"
    echo "  --chunk-size N         Block chunk size in pixels; must divide image width evenly (default: 10)"
    echo ""
    echo "Barcode generation options (only used when generating via -r/-c/-e):"
    echo "  --scale N              Scale factor when no target dimensions set (default: 3)"
    echo "  --padding N            Quiet zone padding in pixels (default: 0)"
    echo "  --text-style STYLE     Data style: mixed, upper, lower, alpha, alnum (default: mixed)"
    echo ""
    echo "Examples:"
    echo "  # Generate a barcode and witness at 1080x720"
    echo "  $0 -r 10 -c 5 -e 2 -W 1080 -H 720"
    echo ""
    echo "  # Use an existing image, auto-detect dimensions via Pillow"
    echo "  $0 -i barcode.png --chunk-size 15 --max-rows 30 --max-cols 10 --max-ec-level 2"
    echo ""
    echo "Notes:"
    echo "  - Must be run inside a Python virtual environment."
    echo "  - rxing-cli must be built: cd external/rxing && cargo build --release -p rxing-cli"
}

# ── Defaults ──────────────────────────────────────────────────────────────────
INPUT_IMAGE=""
OUTPUT_DIR="test-witness"
PARAMS_FILE=""
ROWS=""
COLS=""
EC=""
MAX_ROWS=90
MAX_COLS=30
MAX_EC_LEVEL=8
CHUNK_SIZE=10
IMG_WIDTH=""
IMG_HEIGHT=""
SCALE=3
PADDING=0
TEXT_STYLE="mixed"
MOD=7237005577332262213973186563042994240857116359379907606001950938285454250989

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--image)       INPUT_IMAGE="$2";  shift 2 ;;
        -d|--dir)         OUTPUT_DIR="$2";   shift 2 ;;
        -p|--params)      PARAMS_FILE="$2";  shift 2 ;;
        -r|--rows)        ROWS="$2";         shift 2 ;;
        -c|--cols)        COLS="$2";         shift 2 ;;
        -e|--ec)          EC="$2";           shift 2 ;;
        --max-rows)       MAX_ROWS="$2";     shift 2 ;;
        --max-cols)       MAX_COLS="$2";     shift 2 ;;
        --max-ec-level)   MAX_EC_LEVEL="$2"; shift 2 ;;
        --chunk-size)     CHUNK_SIZE="$2";   shift 2 ;;
        -W|--width)       IMG_WIDTH="$2";    shift 2 ;;
        -H|--height)      IMG_HEIGHT="$2";   shift 2 ;;
        --scale)          SCALE="$2";        shift 2 ;;
        --padding)        PADDING="$2";      shift 2 ;;
        --text-style)     TEXT_STYLE="$2";   shift 2 ;;
        -h|--help)        usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# ── Validate input mode ───────────────────────────────────────────────────────
GENERATING=false
if [ -n "$INPUT_IMAGE" ]; then
    if [ -n "$ROWS" ] || [ -n "$COLS" ] || [ -n "$EC" ]; then
        echo "Error: --image and --rows/--cols/--ec are mutually exclusive"
        exit 1
    fi
    if [ ! -f "$INPUT_IMAGE" ]; then
        echo "Error: Image file not found: $INPUT_IMAGE"
        exit 1
    fi
else
    if [ -z "$ROWS" ] || [ -z "$COLS" ] || [ -z "$EC" ]; then
        echo "Error: Provide either --image FILE or all three of --rows, --cols, --ec"
        usage
        exit 1
    fi
    GENERATING=true
    # When generating, floor the max-* defaults to at least the actual barcode params
    # so params.zok is valid for this barcode out of the box.
    [ "$MAX_ROWS" -lt "$ROWS" ]   && MAX_ROWS="$ROWS"
    [ "$MAX_COLS" -lt "$COLS" ]   && MAX_COLS="$COLS"
    [ "$MAX_EC_LEVEL" -lt "$EC" ] && MAX_EC_LEVEL="$EC"
fi

# ── Python venv check ─────────────────────────────────────────────────────────
if ! python -c 'import sys; exit(0 if sys.prefix != sys.base_prefix else 1)'; then
    echo "Error: Not inside a virtual environment; exiting."
    echo "Please activate a virtual environment and try again."
    exit 1
fi
PYTHON_BIN=$(python -c 'import sys; print(sys.executable)')

mkdir -p "$OUTPUT_DIR"

# ── Step 1 (generate path): create barcode via generate_barcode.py ────────────
if $GENERATING; then
    DIM_SUFFIX=""
    [ -n "$IMG_WIDTH" ] && [ -n "$IMG_HEIGHT" ] && DIM_SUFFIX="_${IMG_WIDTH}x${IMG_HEIGHT}"
    BARCODE_FILE="$OUTPUT_DIR/pdf417_r${ROWS}_c${COLS}_e${EC}${DIM_SUFFIX}.png"

    echo "Step 1: Generating barcode..."
    BARCODE_ARGS="-r $ROWS -c $COLS -e $EC -o $BARCODE_FILE --padding $PADDING --text-style $TEXT_STYLE"
    if [ -n "$IMG_WIDTH" ] && [ -n "$IMG_HEIGHT" ]; then
        BARCODE_ARGS="$BARCODE_ARGS --width $IMG_WIDTH --height $IMG_HEIGHT"
    else
        BARCODE_ARGS="$BARCODE_ARGS --scale $SCALE"
    fi
    ${PYTHON_BIN} python-scripts/generate_barcode.py $BARCODE_ARGS
    echo "✓ Barcode generated: $BARCODE_FILE"
    echo ""

    INPUT_IMAGE="$BARCODE_FILE"
else
    echo "Step 1: Using existing image: $INPUT_IMAGE"
    echo ""
fi

# ── Detect image dimensions if not yet known ──────────────────────────────────
if [ -z "$IMG_WIDTH" ] || [ -z "$IMG_HEIGHT" ]; then
    echo "Auto-detecting image dimensions from '$INPUT_IMAGE'..."
    if ! ${PYTHON_BIN} -c 'from PIL import Image' 2>/dev/null; then
        echo "Error: Pillow is not installed. Run: pip install Pillow"
        exit 1
    fi
    read -r IMG_WIDTH IMG_HEIGHT < <(
        _IMG_PATH="$INPUT_IMAGE" ${PYTHON_BIN} - <<'PYEOF'
from PIL import Image
import os
with Image.open(os.environ["_IMG_PATH"]) as img:
    print(img.width, img.height)
PYEOF
    )
    echo "Detected dimensions: ${IMG_WIDTH}x${IMG_HEIGHT}"
    echo ""
fi

# ── Validate chunk-size divides image width ───────────────────────────────────
if (( IMG_WIDTH % CHUNK_SIZE != 0 )); then
    SUGGESTIONS=$(${PYTHON_BIN} -c "
w = $IMG_WIDTH; cs = $CHUNK_SIZE
divs = sorted([d for d in range(1, w+1) if w % d == 0], key=lambda d: abs(d-cs))[:5]
print(', '.join(map(str, divs)))")
    echo "Error: --chunk-size $CHUNK_SIZE does not evenly divide image width $IMG_WIDTH"
    echo "Nearest valid chunk sizes for width $IMG_WIDTH: $SUGGESTIONS"
    exit 1
fi

# ── Derive output filenames from input image basename ─────────────────────────
IMAGE_STEM=$(basename "$INPUT_IMAGE" | sed 's/\.[^.]*$//')
WITNESS_JSON="$OUTPUT_DIR/${IMAGE_STEM}_witness.json"
WITNESS_PIN="$OUTPUT_DIR/${IMAGE_STEM}_witness.pin"
WITNESS_VIN="$OUTPUT_DIR/${IMAGE_STEM}_witness.vin"
: "${PARAMS_FILE:="$OUTPUT_DIR/params.zok"}"

# ── Summary ───────────────────────────────────────────────────────────────────
echo "Witness Generation"
echo "=================="
echo "Input image  : $INPUT_IMAGE"
echo "Dimensions   : ${IMG_WIDTH}x${IMG_HEIGHT}"
echo "Chunk size   : $CHUNK_SIZE"
echo "Max rows     : $MAX_ROWS"
echo "Max cols     : $MAX_COLS"
echo "Max EC level : $MAX_EC_LEVEL"
echo "Output dir   : $OUTPUT_DIR"
echo "params.zok   : $PARAMS_FILE"
echo ""

# ── Step 2: Generate params.zok ───────────────────────────────────────────────
echo "Step 2: Generating params.zok..."
(
    cd external/rxing
    cargo run --release -p rxing-cli -- /dev/null generate-params \
        "../../$PARAMS_FILE" \
        --image-width  "$IMG_WIDTH" \
        --image-height "$IMG_HEIGHT" \
        --max-rows     "$MAX_ROWS" \
        --max-cols     "$MAX_COLS" \
        --max-ec-level "$MAX_EC_LEVEL" \
        --chunk-size   "$CHUNK_SIZE"
)
echo "✓ params.zok written: $PARAMS_FILE"
echo ""

# ── Step 3: Decode barcode and save witness JSON ──────────────────────────────
echo "Step 3: Decoding barcode and generating witness JSON..."
(
    cd external/rxing
    cargo run --release -p rxing-cli -- \
        "../../$INPUT_IMAGE" decode \
        --barcode-types PDF_417 \
        --save-witness "../../$WITNESS_JSON" \
        --image-mode custom \
        --image-width  "$IMG_WIDTH" \
        --image-height "$IMG_HEIGHT" \
        --max-rows     "$MAX_ROWS" \
        --max-cols     "$MAX_COLS" \
        --max-ec-level "$MAX_EC_LEVEL" \
        --chunk-size   "$CHUNK_SIZE"
)
echo "✓ Witness JSON written: $WITNESS_JSON"
echo ""

# ── Step 4: Convert witness JSON to .pin / .vin ───────────────────────────────
echo "Step 4: Converting witness JSON to .pin and .vin files..."
${PYTHON_BIN} python-scripts/json_to_witness.py \
    -i "$WITNESS_JSON" \
    --type bin_image=bool \
    --public wb_words \
    --public garbage_words \
    --public wb_disjoint_set_poly_f \
    --public garbage_disjoint_set_poly_f \
    --modulus "$MOD" \
    --pin "$WITNESS_PIN" \
    --vin "$WITNESS_VIN"
echo "✓ Witness files written:"
echo "  - $WITNESS_PIN"
echo "  - $WITNESS_VIN"
echo ""

echo "========================================"
echo "✓ All done!"
echo "========================================"
echo ""
echo "Generated files in $OUTPUT_DIR/:"
ls -lh "$OUTPUT_DIR/"
