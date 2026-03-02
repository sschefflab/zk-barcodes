#!/usr/bin/env python3

"""
Generate tables needed for lookups for block measurement.
"""

B = 1080
L = 10


def generate_powers_of_B():
    return [[i, B**i] for i in range(0, L)]


def generate_pixels_and_blocks():
    table = []
    for i in range(0, 2**L):
        c = i

        binary = format(i, f"0{L}b")  # zero-padded L-bit string
        previous = binary[0]
        num_bits = 1
        enc_baseB = 0
        power_of_B = 0

        for b in range(1, len(binary)):
            if binary[b] == previous:
                num_bits += 1
            else:
                enc_baseB += B**power_of_B * num_bits
                power_of_B += 1
                num_bits = 1
                previous = binary[b]

        r = num_bits
        nb = power_of_B
        odd = int(nb % 2 == 1)
        black = int(previous == "0")
        table.append([c, enc_baseB, r, nb, odd, black])

    return table


if __name__ == "__main__":
    powers_of_B = generate_powers_of_B()
    print("POWERS_OF_B:")
    print(powers_of_B)
    print()

    pixels_and_blocks = generate_pixels_and_blocks()
    print("PIXELS_AND_BLOCKS:")
    print(pixels_and_blocks)
    print()
