#!/usr/bin/env python3

"""
Generate tables needed for lookups for block measurement.
"""

L = 10


def generate_powers_of_B(B):
    return [[i, B**i] for i in range(0, L)]


def generate_pixels_and_blocks(B):
    table = []
    for i in range(0, 2**L):
        c = i

        binary = format(
            i, f"0{L}b"
        )  # zero-padded L-bit string, binary[0]=pixel[0]=leftmost
        previous = binary[0]  # start at leftmost pixel (MSB of integer)
        num_bits = 1
        blocks = []  # completed (non-remainder) blocks, left to right
        for b in range(1, len(binary)):  # iterate toward rightmost pixel (LSB)
            if binary[b] == previous:
                num_bits += 1
            else:
                blocks.append(num_bits)
                num_bits = 1
                previous = binary[b]

        r = num_bits  # remainder = rightmost block
        nb = len(blocks)  # number of completed blocks, not including the remainder
        odd = int(nb % 2 == 1)
        black = int(previous == "1")  # 1 if rightmost (remainder) block is black

        # Big-endian base-B encoding: leftmost block gets B^(nb-1), rightmost gets B^0
        enc_baseB = sum(B ** (nb - 1 - j) * s for j, s in enumerate(blocks))

        table.append([c, enc_baseB, r, nb, odd, black])

    return table


if __name__ == "__main__":
    for B in [104, 1080]:
        print(f"=== B = {B} ===")
        print()

        powers_of_B = generate_powers_of_B(B)
        print("POWERS_OF_B:")
        print(powers_of_B)
        print()

        pixels_and_blocks = generate_pixels_and_blocks(B)
        print("PIXELS_AND_BLOCKS:")
        print(pixels_and_blocks)
        print()
