from math import ceil, log2

from block_measurement_arrays import generate_pixels_and_blocks

# The inputs / variables that can change.
# The numbers presented here are the maximum we are considering.
# All other constants are computed from these.

IMAGE_WIDTH = 1080  # how wide the image is in pixels
IMAGE_HEIGHT = 720  # how tall the image is in pixels
MAX_NUM_ROWS = 90  # the max number of logical barcode rows the barcode may have
MAX_NUM_COLS = 30  # the max number of data columns the barcode may have
MAX_EC_LEVEL = 8  # the max error correction level the barcode may use

# A constant that we use for all input sizes - the width, in pixels of one "chunk" for block measurement
L = 10
table_len = 2**L

num_chunks = ceil(IMAGE_WIDTH / L)  # the number of block measurement chunks per row

garbage_rows = MAX_NUM_ROWS - 1  # the max number of garbage rows the barcode may have

garbage_b = IMAGE_WIDTH + 1  # the base used for chunk encoding garbage blocks.
# It is computed as the max number of pixels in a block plus 1.

garbage_m = L  # the max number of blocks that may be in a block measurement chunk
garbage_nb = IMAGE_WIDTH  # the max number of blocks that may be in a garbage row
garbage_logm = ceil(log2(garbage_m))
garbage_col_words = ceil(IMAGE_WIDTH / 8)

garbage_powers_of_b = [(i, garbage_b**i) for i in range(garbage_m)]
garbage_chunk_lookup = generate_pixels_and_blocks(
    garbage_b
)  # a complicated lookup table of data about possible chunks of size L for garbage chunks. Look at this function definition for the details.

# Same constants as above, but for well-behaved rows

wb_b = (
    ceil(IMAGE_WIDTH / 85) * 8 + 1
)  # minimum 17*5 = 85 modules in a row, regardless of barcode size.
# Divide into image_width to get pixels/module, multiply by 8 to get pixels in max block, add 1.

wb_nb = (
    8 * MAX_NUM_COLS + 24 + 9
)  # 8 blocks per data column + 24 blocks for start and row indicators + 9 blocks for stop

wb_m = min(
    ceil(L / (IMAGE_WIDTH / wb_nb)), L
)  # M tops out at L, but it may be lower for wb rows

wb_logm = ceil(log2(wb_m))
wb_col_words = ceil(wb_nb / 8)

wb_powers_of_b = [(i, wb_b**i) for i in range(wb_m)]
wb_chunk_lookup = generate_pixels_and_blocks(wb_b)

max_words = MAX_NUM_ROWS * MAX_NUM_COLS  # maximum number of words in the barcode

max_ec_words = 2 ** (
    MAX_EC_LEVEL + 1
)  # maximum number of error correction codewords in the barcode

qbits = ceil(
    log2(max_words * 929)
)  # the maximum number of bits in the quotient part of a error correction polynomial evaluation

print("successfully computed all constants")
