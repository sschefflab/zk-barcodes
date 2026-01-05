#!/usr/bin/env python3
"""
Generate encoded character lookup table for PDF417 Text Compaction Mode.

Encoding scheme:
encoded_val = next_next_table*2^16 + next_table*2^14 + this_table*2^12 + char*2^5 + base30_val

Where:
- base30_val: 0-29 (codeword value within sub-mode)
- this_table: 0-3 (current sub-mode: 0=Alpha, 1=Lower, 2=Mixed, 3=Punctuation)
- char: 0-127 (ASCII character value, or 0 for mode switches)
- next_table: 0-3 (next sub-mode)
- next_next_table: 0-3 (sub-mode after shift returns)
"""

# PDF417 Text Compaction Mode - Flattened Interpretation Table
# Contains 4 sub-modes x 30 values each = 120 total entries
# Order: Alpha (0-29), Lower (30-59), Mixed (60-89), Punctuation (90-119)
TEXT_MODE_TABLE = [
    # Alpha sub-mode (0-29)
    65, 66, 67, 68, 69, 70, 71, 72, 73, 74,  # A-J
    75, 76, 77, 78, 79, 80, 81, 82, 83, 84,  # K-T
    85, 86, 87, 88, 89, 90,                   # U-Z
    32,                                        # space
    0, 0, 0,                                   # ll, ml, ps

    # Lower sub-mode (30-59)
    97, 98, 99, 100, 101, 102, 103, 104, 105, 106,  # a-j
    107, 108, 109, 110, 111, 112, 113, 114, 115, 116,  # k-t
    117, 118, 119, 120, 121, 122,              # u-z
    32,                                         # space
    0, 0, 0,                                    # as, ml, ps

    # Mixed sub-mode (60-89)
    48, 49, 50, 51, 52, 53, 54, 55, 56, 57,   # 0-9
    38, 13, 9, 44, 58, 35, 45, 46, 36, 47,    # &, CR, HT, etc.
    43, 37, 42, 61, 94,                        # +, %, *, =, ^
    0,                                          # pl
    32,                                         # space
    0, 0, 0,                                    # ll, al, ps

    # Punctuation sub-mode (90-119)
    59, 60, 62, 64, 91, 92, 93, 95, 96, 126,  # ;, <, >, @, [, \, ], _, `, ~
    33, 13, 9, 44, 58, 10, 45, 46, 36, 47,    # !, CR, HT, ,, :, LF, etc.
    34, 124, 42, 40, 41, 63, 123, 125, 39,    # ", |, *, (, ), ?, {, }, '
    0                                           # al
]

NEXT_MODE_TABLE = [
    # Alpha sub-mode (0-29, current mode = 0)
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0,
    1, 2, 3,

    # Lower sub-mode (30-59, current mode = 1)
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1,
    0, 2, 3,

    # Mixed sub-mode (60-89, current mode = 2)
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2,
    3, 2, 1, 0, 3,

    # Punctuation sub-mode (90-119, current mode = 3)
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3,
    0
]

NEXT_NEXT_MODE_TABLE = [
    # Alpha sub-mode (0-29, current mode = 0)
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0,
    1, 2, 0,

    # Lower sub-mode (30-59, current mode = 1)
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1,
    1, 2, 1,

    # Mixed sub-mode (60-89, current mode = 2)
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2,
    3, 2, 1, 0, 2,

    # Punctuation sub-mode (90-119, current mode = 3)
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3,
    0
]

def encode_entry(base30_val, this_table, char, next_table, next_next_table):
    """Encode a character lookup entry."""
    return (next_next_table << 16) + (next_table << 14) + (this_table << 12) + (char << 5) + base30_val

def generate_encoded_table():
    """Generate all 120 encoded entries."""
    encoded_values = []

    for index in range(120):
        base30_val = index % 30
        this_table = index // 30
        char = TEXT_MODE_TABLE[index]
        next_table = NEXT_MODE_TABLE[index]
        next_next_table = NEXT_NEXT_MODE_TABLE[index]

        encoded = encode_entry(base30_val, this_table, char, next_table, next_next_table)
        encoded_values.append(encoded)

    return encoded_values

if __name__ == "__main__":
    encoded_table = generate_encoded_table()
    print(encoded_table)
