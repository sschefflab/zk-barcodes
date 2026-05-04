"""
Generate pre-built witness files for binarize.zok tests.

Run from the repo root:
    python tests/witnesses/generate_binarize.py

Outputs .pin and .vin files into tests/witnesses/binarize/.
One witness file per test in test_binarize.py.
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import json_to_witness

OUT = Path(__file__).parent / "binarize"
OUT.mkdir(exist_ok=True)

# Must match the constants in tests/zok_wrappers/test_binarize.zok
R, C = 4, 8


def uniform(image_val: int, bin_val: int) -> dict:
    return {
        "image":     [[image_val] * C for _ in range(R)],
        "bin_image": [[bin_val]   * C for _ in range(R)],
    }


def mixed() -> dict:
    """Left half dark (200, bin=0), right half light (50, bin=1)."""
    image     = [[200 if c < C // 2 else 50 for c in range(C)] for _ in range(R)]
    bin_image = [[0   if c < C // 2 else 1  for c in range(C)] for _ in range(R)]
    return {"image": image, "bin_image": bin_image}


def mutate(witness: dict, row: int, col: int, new_bin: int) -> dict:
    w = copy.deepcopy(witness)
    w["bin_image"][row][col] = new_bin
    return w


witnesses = {
    # --- happy path ---
    "happy_all_dark":              uniform(200, 0),   # dark pixel, correct bin=0
    "happy_all_light":             uniform(50,  1),   # light pixel, correct bin=1
    "happy_mixed":                 mixed(),            # left dark / right light

    # --- cheating ---
    "cheat_dark_as_white":         uniform(200, 1),   # dark pixel claimed white
    "cheat_light_as_black":        uniform(50,  0),   # light pixel claimed black
    "cheat_nonbinary":             uniform(100, 2),   # bin_image=2, not 0 or 1
    "cheat_single_pixel":          mutate(mixed(), 0, 0, 1),          # flip pixel (0,0): dark→claimed white
    "cheat_last_pixel":            mutate(mixed(), R-1, C-1, 0),      # flip pixel (R-1,C-1): light→claimed black

    # --- edge cases ---
    "edge_127_white":              uniform(127, 1),   # max light pixel, bin=1
    "edge_128_black":              uniform(128, 0),   # min dark pixel, bin=0
    "edge_0_white":                uniform(0,   1),   # fully white pixel, bin=1
    "edge_255_black":              uniform(255, 0),   # fully black pixel, bin=0
    "edge_127_claimed_black":      uniform(127, 0),   # 127 wrongly claimed as black
    "edge_128_claimed_white":      uniform(128, 1),   # 128 wrongly claimed as white
}

for name, witness in witnesses.items():
    pin, vin = json_to_witness(witness, OUT / f"{name}.json")
    print(f"  {name}: {pin.name}, {vin.name}")
