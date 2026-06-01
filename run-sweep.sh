#!/bin/bash

set -euo pipefail

# ── Sweep axes ────────────────────────────────────────────────────────────────
# Format: "IMG_WIDTHxIMG_HEIGHT:TARGET_WIDTHxTARGET_HEIGHT"
IMAGE_SIZES=(
    "144x48:144x48"
    "192x144:192x144"
    "384x288:384x288"
    "640x480:640x480"
    "1080x720:1080x720"
    # add more entries here
)

# Format: "MAX_ROWSxMAX_COLS"
MAX_ROW_COL_SETS=(
    "3x3"
    "10x6"
    "21x13"
    "60x20"
    "90x30"
    # add more entries here
)

MAX_EC_LEVELS=(0 1 5 8)

# ── Default actual barcode dimensions (capped by max values) ──────────────────
DEFAULT_ROWS=21
DEFAULT_COLS=13
DEFAULT_EC=5

# ── Validity guard ─────────────────────────────────────────────────────────────
# Return 1 to skip a combination, 0 to run it.
# Edit this function to encode real constraints between axes.
is_valid() {
    local img_w=$1 img_h=$2 max_rows=$3 max_cols=$4 max_ec=$5
    (( max_rows <= img_h && max_cols <= img_w )) || return 1
    # need at least 1 data codeword + 1 SLD + ec codewords
    (( max_rows * max_cols > (1 << (max_ec + 1)) + 1 )) || return 1
    # actual barcode must fit in canvas at scale=1 (minimum possible size)
    local actual_rows actual_cols
    actual_rows=$(( DEFAULT_ROWS < max_rows ? DEFAULT_ROWS : max_rows ))
    actual_cols=$(( DEFAULT_COLS < max_cols ? DEFAULT_COLS : max_cols ))
    local min_w min_h
    min_w=$(( 17 * (actual_cols + 4) ))
    min_h=$actual_rows
    (( min_w <= img_w && min_h <= img_h )) || return 1
    return 0
}

# ── Sweep ─────────────────────────────────────────────────────────────────────
SKIPPED=0
RAN=0
FAILED=0

for img_spec in "${IMAGE_SIZES[@]}"; do
    img_dims="${img_spec%%:*}"
    target_dims="${img_spec##*:}"
    img_w="${img_dims%%x*}"; img_h="${img_dims##*x}"
    tgt_w="${target_dims%%x*}"; tgt_h="${target_dims##*x}"

    for rc_spec in "${MAX_ROW_COL_SETS[@]}"; do
        max_rows="${rc_spec%%x*}"; max_cols="${rc_spec##*x}"

        for max_ec in "${MAX_EC_LEVELS[@]}"; do

            if ! is_valid "$img_w" "$img_h" "$max_rows" "$max_cols" "$max_ec"; then
                echo "Skipping: image=${img_dims} max_rows=${max_rows} max_cols=${max_cols} max_ec=${max_ec}"
                (( SKIPPED++ )) || true
                continue
            fi

            rows=$(( DEFAULT_ROWS < max_rows ? DEFAULT_ROWS : max_rows ))
            cols=$(( DEFAULT_COLS < max_cols ? DEFAULT_COLS : max_cols ))
            ec=$(( DEFAULT_EC < max_ec ? DEFAULT_EC : max_ec ))

            echo "========================================"
            echo "Sweep: image=${img_dims} max_rows=${max_rows} max_cols=${max_cols} max_ec=${max_ec} rows=${rows} cols=${cols} ec=${ec}"
            echo "========================================"

            if IMG_WIDTH="$img_w"                      \
               IMG_HEIGHT="$img_h"                     \
               TARGET_BARCODE_WIDTH="$tgt_w"           \
               TARGET_BARCODE_HEIGHT="$tgt_h"          \
               MAX_ROWS="$max_rows"                    \
               MAX_COLS="$max_cols"                    \
               MAX_EC_LEVEL="$max_ec"                  \
               ROWS="$rows"                            \
               COLS="$cols"                            \
               EC="$ec"                                \
               DRY_RUN="${DRY_RUN:-0}"                 \
               ./run-benchmark.sh; then
                (( RAN++ )) || true
            else
                echo "FAILED: image=${img_dims} max_rows=${max_rows} max_cols=${max_cols} max_ec=${max_ec} rows=${rows} cols=${cols} ec=${ec}"
                (( FAILED++ )) || true
            fi
        done
    done
done

echo "========================================"
echo "Sweep complete: $RAN succeeded, $FAILED failed, $SKIPPED skipped."
echo "========================================"
