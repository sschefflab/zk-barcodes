# NOT USED - just python versions of some functions that are easier to read here than in their original forms

MODULES_IN_CODEWORD = 17
BARS_IN_MODULE = 8


def sample_bit_counts(blocks: list[int]) -> list[int]:
    pixel_sum = sum(blocks)
    result = [0] * BARS_IN_MODULE
    index = 0
    sum_prev_pixels = 0

    for i in range(MODULES_IN_CODEWORD):
        sample_index = pixel_sum * (2 * i + 1) / (2 * MODULES_IN_CODEWORD)
        if sum_prev_pixels + blocks[index] <= sample_index:
            sum_prev_pixels += blocks[index]
            index += 1
        result[index] += 1

    return result


def check_sample_bit_counts(blocks: list[int], norm_blocks: list[int]):
    pixel_sum = sum(blocks)
    sum_prev_pixels = blocks[0]
    sum_prev_modules = norm_blocks[0]

    for i in range(1, 8):
        lower_bound = (
            pixel_sum * (2 * sum_prev_modules - 1) / 34
        )  # position of previous sample point
        upper_bound = (
            pixel_sum * (2 * sum_prev_modules + 1) / 34
        )  # position of next sample point

        assert lower_bound < sum_prev_pixels
        assert upper_bound >= sum_prev_pixels

        sum_prev_pixels += blocks[i]
        sum_prev_modules += norm_blocks[i]
