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
    65,
    66,
    67,
    68,
    69,
    70,
    71,
    72,
    73,
    74,  # A-J
    75,
    76,
    77,
    78,
    79,
    80,
    81,
    82,
    83,
    84,  # K-T
    85,
    86,
    87,
    88,
    89,
    90,  # U-Z
    32,  # space
    0,
    0,
    0,  # ll, ml, ps
    # Lower sub-mode (30-59)
    97,
    98,
    99,
    100,
    101,
    102,
    103,
    104,
    105,
    106,  # a-j
    107,
    108,
    109,
    110,
    111,
    112,
    113,
    114,
    115,
    116,  # k-t
    117,
    118,
    119,
    120,
    121,
    122,  # u-z
    32,  # space
    0,
    0,
    0,  # as, ml, ps
    # Mixed sub-mode (60-89)
    48,
    49,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,  # 0-9
    38,
    13,
    9,
    44,
    58,
    35,
    45,
    46,
    36,
    47,  # &, CR, HT, etc.
    43,
    37,
    42,
    61,
    94,  # +, %, *, =, ^
    0,  # pl
    32,  # space
    0,
    0,
    0,  # ll, al, ps
    # Punctuation sub-mode (90-119)
    59,
    60,
    62,
    64,
    91,
    92,
    93,
    95,
    96,
    126,  # ;, <, >, @, [, \, ], _, `, ~
    33,
    13,
    9,
    44,
    58,
    10,
    45,
    46,
    36,
    47,  # !, CR, HT, ,, :, LF, etc.
    34,
    124,
    42,
    40,
    41,
    63,
    123,
    125,
    39,  # ", |, *, (, ), ?, {, }, '
    0,  # al
]

NEXT_MODE_TABLE = [
    # Alpha sub-mode (0-29, current mode = 0)
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    2,
    3,
    # Lower sub-mode (30-59, current mode = 1)
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    2,
    3,
    # Mixed sub-mode (60-89, current mode = 2)
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    3,
    2,
    1,
    0,
    3,
    # Punctuation sub-mode (90-119, current mode = 3)
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    0,
]

NEXT_NEXT_MODE_TABLE = [
    # Alpha sub-mode (0-29, current mode = 0)
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    2,
    0,
    # Lower sub-mode (30-59, current mode = 1)
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    2,
    1,
    # Mixed sub-mode (60-89, current mode = 2)
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    3,
    2,
    1,
    0,
    2,
    # Punctuation sub-mode (90-119, current mode = 3)
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    0,
]


def encode_entry(base30_val, this_table, char, next_table, next_next_table):
    """Encode a character lookup entry."""
    return (
        (next_next_table << 16)
        + (next_table << 14)
        + (this_table << 12)
        + (char << 5)
        + base30_val
    )


# Special states (order in barcode: zeros | SLD | data | pads | ec)
# ZERO_TABLE_STATE: all zeros, used before decoding starts
ZERO_STATE_ENCODED = encode_entry(0, 0, 0, 0, 0)  # = 0

# SLD_TABLE_STATE: char=95, used for symbol length descriptor (first data codeword)
SLD_STATE_ENCODED = encode_entry(0, 0, 95, 0, 0)  # = 3040

# PAD_TABLE_STATE: char=32 (space), used for pad codewords between data and EC
PAD_STATE_ENCODED = encode_entry(0, 0, 32, 0, 0)  # = 1024

# EC_TABLE_STATE: char=6, used for error correction codewords at the end
EC_STATE_ENCODED = encode_entry(0, 0, 6, 0, 0)  # = 192


def generate_encoded_table():
    """Generate all 120 encoded entries plus special states."""
    encoded_values = []

    for index in range(120):
        base30_val = index % 30
        this_table = index // 30
        char = TEXT_MODE_TABLE[index]
        next_table = NEXT_MODE_TABLE[index]
        next_next_table = NEXT_NEXT_MODE_TABLE[index]

        encoded = encode_entry(
            base30_val, this_table, char, next_table, next_next_table
        )
        encoded_values.append(encoded)

    # Special states
    encoded_values.append(ZERO_STATE_ENCODED)  # Dummy state before SLD
    encoded_values.append(SLD_STATE_ENCODED)  # SLD state for symbol length descriptor
    encoded_values.append(PAD_STATE_ENCODED)  # Pad state between data and EC
    encoded_values.append(EC_STATE_ENCODED)  # EC state for error correction
    return encoded_values


def get_state_components(index):
    """Get all components of a state by its index (0-119)."""
    base30_val = index % 30
    this_table = index // 30
    char = TEXT_MODE_TABLE[index]
    next_table = NEXT_MODE_TABLE[index]
    next_next_table = NEXT_NEXT_MODE_TABLE[index]
    return base30_val, this_table, char, next_table, next_next_table


def encode_state_tuple(encoded1, encoded2):
    """Encode a tuple of two states as a single field element.

    Matches the ZoKrates function:
    encoded1 * 2**18 + encoded2
    """
    return (encoded1 << 18) + encoded2


def is_valid_transition(state1_idx, state2_idx):
    """Check if transitioning from state1 to state2 is valid.

    Based on codewords_to_chars.zok logic:
    - state1.next_table == state2.this_table (always required)
    - If state2.char != 0: state1.next_next_table == state2.next_table
    """
    _, _, _, next_table1, next_next_table1 = get_state_components(state1_idx)
    _, this_table2, char2, next_table2, _ = get_state_components(state2_idx)

    # Condition 1: next_table of state1 must equal this_table of state2
    if next_table1 != this_table2:
        return False

    # Condition 2: if state2.char != 0, then next_next_table1 == next_table2
    if char2 != 0 and next_next_table1 != next_table2:
        return False

    return True


def generate_valid_transitions():
    """Generate all valid state transition tuples encoded as field elements."""
    encoded_table = generate_encoded_table()
    valid_transitions = []

    # Normal state transitions (indices 0-119)
    for idx1 in range(120):
        for idx2 in range(120):
            if is_valid_transition(idx1, idx2):
                encoded_tuple = encode_state_tuple(
                    encoded_table[idx1], encoded_table[idx2]
                )
                valid_transitions.append(encoded_tuple)

    # Dummy state (ZERO_STATE_ENCODED) transitions:
    # - ZERO -> ZERO is allowed (stay in zero state)
    valid_transitions.append(encode_state_tuple(ZERO_STATE_ENCODED, ZERO_STATE_ENCODED))

    # - ZERO -> SLD is allowed (transition to symbol length descriptor)
    valid_transitions.append(encode_state_tuple(ZERO_STATE_ENCODED, SLD_STATE_ENCODED))

    # SLD state transitions:
    # - SLD -> SLD is allowed (intra-codeword: state1=SLD, state2=SLD for the one SLD codeword)
    #   The circuit separately asserts there are exactly 2 SLD states total.
    valid_transitions.append(encode_state_tuple(SLD_STATE_ENCODED, SLD_STATE_ENCODED))

    # - SLD -> Alpha is allowed (transition from SLD to start of actual data)
    #   Alpha states are indices 0-29
    for idx in range(30):
        encoded_tuple = encode_state_tuple(SLD_STATE_ENCODED, encoded_table[idx])
        valid_transitions.append(encoded_tuple)

    # PAD state transitions:
    # - PAD -> PAD is allowed (stay in pad state)
    valid_transitions.append(encode_state_tuple(PAD_STATE_ENCODED, PAD_STATE_ENCODED))

    # - any normal state -> PAD is allowed (transition into padding at end of data)
    for idx in range(120):
        encoded_tuple = encode_state_tuple(encoded_table[idx], PAD_STATE_ENCODED)
        valid_transitions.append(encoded_tuple)

    # - any normal state -> EC is allowed (data can end without padding, in any sub-mode)
    for idx in range(120):
        encoded_tuple = encode_state_tuple(encoded_table[idx], EC_STATE_ENCODED)
        valid_transitions.append(encoded_tuple)

    # - PAD -> EC is allowed (transition from padding to error correction)
    valid_transitions.append(encode_state_tuple(PAD_STATE_ENCODED, EC_STATE_ENCODED))

    # EC state transitions:
    # - EC -> EC is allowed (stay in EC state)
    valid_transitions.append(encode_state_tuple(EC_STATE_ENCODED, EC_STATE_ENCODED))

    return valid_transitions


if __name__ == "__main__":
    encoded_table = generate_encoded_table()
    print("ENCODED_STATE_MACHINE:")
    print(encoded_table)
    print()

    valid_transitions = generate_valid_transitions()
    print(f"VALID_TRANSITIONS ({len(valid_transitions)} entries):")
    print(valid_transitions)
