#!/usr/bin/env python3

"""
Generate tables needed for lookups for block measurement.
"""


def generate_powers_of_B(B, L):
    return [[i, B**i] for i in range(0, L)]


def generate_pixels_and_blocks(B, L):
    table = []
    for i in range(0, 2**L):
        c = i

        binary = format(i, f"0{L}b")[
            ::-1
        ]  # zero-padded L-bit string reversed: binary[0]=pixel[0]=LSB (little-endian)
        previous = binary[0]  # start at leftmost pixel
        num_bits = 1
        blocks = []  # completed (non-remainder) blocks, left to right
        for b in range(1, len(binary)):  # iterate toward rightmost pixel
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

        # Little-endian base-B encoding: leftmost block gets B^0, rightmost gets B^(nb-1)
        enc_baseB = sum(B**j * s for j, s in enumerate(blocks))

        table.append([c, enc_baseB, r, nb, odd, black])

    return table


if __name__ == "__main__":
    # (B, L) pairs: HD uses L=10, SD uses L=10, SMALL uses L=8
    for B, L in [(25, 8), (65, 10), (105, 10), (193, 8), (640, 10), (1081, 10)]:
        print(f"=== B = {B}, L = {L} ===")
        print()

        powers_of_B = generate_powers_of_B(B, L)
        print("POWERS_OF_B:")
        print(powers_of_B)
        print()

        pixels_and_blocks = generate_pixels_and_blocks(B, L)
        print("PIXELS_AND_BLOCKS:")
        print(pixels_and_blocks)
        print()
