"""
Tests for zokrates/binarize.zok
================================

The circuit checks that a binary (0/1) image is consistent with the
original grayscale image using a fixed threshold of 128:

    bin_image[r][c] = 0  (black bar)  iff  image[r][c] in [128, 255]
    bin_image[r][c] = 1  (white bar)  iff  image[r][c] in [0, 127]

ZoKrates constraint (per pixel):
    1.  bin_image * (1 - bin_image) == 0      (must be 0 or 1)
    2.  to_lookup = image - 128*(1-bin_image)  (= image-128 if black, = image if white)
        value_in_array(to_lookup, RANGE_0_128) (must be in [0..127])

Pre-generated witnesses live in tests/witnesses/binarize/.
Regenerate them with:
    python tests/witnesses/generate_binarize.py

Running
-------
    pytest tests/test_binarize.py              # all binarize tests
    pytest tests/test_binarize.py -k "happy"  # only happy-path tests
    pytest tests/test_binarize.py -k "cheat"  # only cheating tests
    pytest tests/test_binarize.py -k "edge"   # only edge-case tests
    pytest tests/test_binarize.py --no-setup  # skip compile (keys must exist)
"""

import pytest

from helpers import (
    REPO_ROOT,
    WITNESSES_DIR,
    compile_and_setup,
    prove_and_verify,
)

ZOK_FILE = REPO_ROOT / "tests" / "zok_wrappers" / "test_binarize.zok"
W_DIR = WITNESSES_DIR / "binarize"


# ---------------------------------------------------------------------------
# Session-level fixture: compile the circuit once per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def binarize_circuit(request):
    """Compile binarize.zok and return its basename for prove/verify calls."""
    skip_setup = request.config.getoption("--no-setup")
    return compile_and_setup(ZOK_FILE, skip=skip_setup)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _witness(name: str):
    """Return (pin_path, vin_path) for a pre-generated binarize witness."""
    pin = W_DIR / f"{name}.pin"
    vin = W_DIR / f"{name}.vin"
    if not pin.exists() or not vin.exists():
        pytest.fail(
            f"Pre-generated witness '{name}' not found in {W_DIR}. "
            "Run: python tests/witnesses/generate_binarize.py"
        )
    return pin, vin


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_happy_all_dark(binarize_circuit, tmp_path):
    """
    All pixels are dark (200 >= 128) → bin_image all 0.

    to_lookup = 200 - 128*(1-0) = 72  ∈ [0,127] ✓
    """
    pin, vin = _witness("happy_all_dark")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


def test_happy_all_light(binarize_circuit, tmp_path):
    """
    All pixels are light (50 < 128) → bin_image all 1.

    to_lookup = 50 - 128*(1-1) = 50  ∈ [0,127] ✓
    """
    pin, vin = _witness("happy_all_light")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


def test_happy_mixed(binarize_circuit, tmp_path):
    """
    Left half dark, right half light — realistic barcode pattern.
    Both halves have correct binarization.
    """
    pin, vin = _witness("happy_mixed")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


# ---------------------------------------------------------------------------
# Cheating tests — the prover tries to lie about the binarization
# ---------------------------------------------------------------------------

def test_cheat_dark_pixel_claimed_white(binarize_circuit, tmp_path):
    """
    ATTACK: claim bin_image=1 (white) for a dark pixel (image=200).

    to_lookup = 200 - 128*(1-1) = 200  NOT in [0,127] → constraint fails.
    """
    pin, vin = _witness("cheat_dark_as_white")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")


def test_cheat_light_pixel_claimed_black(binarize_circuit, tmp_path):
    """
    ATTACK: claim bin_image=0 (black) for a light pixel (image=50).

    to_lookup = 50 - 128*(1-0) = -78  NOT in [0,127] → constraint fails.
    """
    pin, vin = _witness("cheat_light_as_black")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")


def test_cheat_non_binary_bin_value(binarize_circuit, tmp_path):
    """
    ATTACK: set bin_image=2 (neither 0 nor 1).

    Constraint: bin_image*(1 - bin_image) = 2*(1-2) = -2 ≠ 0 → fails.
    """
    pin, vin = _witness("cheat_nonbinary")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")


def test_cheat_single_pixel_flipped(binarize_circuit, tmp_path):
    """
    ATTACK: all pixels correct except one — bin_image[0][0] flipped.

    image[0][0]=200 (dark), claimed bin=1 (should be 0).
    The circuit checks every pixel: this single error must be caught.
    """
    pin, vin = _witness("cheat_single_pixel")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")


def test_cheat_last_pixel_flipped(binarize_circuit, tmp_path):
    """
    ATTACK: flip the binarization of the last pixel (R-1, C-1).

    image[R-1][C-1]=50 (light), claimed bin=0 (should be 1).
    Ensures the circuit checks all pixels, not just early ones.
    """
    pin, vin = _witness("cheat_last_pixel")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")


# ---------------------------------------------------------------------------
# Edge-case tests — boundary pixel values
# ---------------------------------------------------------------------------

def test_edge_pixel_127_is_white(binarize_circuit, tmp_path):
    """
    Pixel value 127 is the maximum light pixel.  bin_image must be 1.

    to_lookup = 127 - 128*(1-1) = 127  ∈ [0,127] ✓  (just fits)
    """
    pin, vin = _witness("edge_127_white")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


def test_edge_pixel_128_is_black(binarize_circuit, tmp_path):
    """
    Pixel value 128 is the minimum dark pixel.  bin_image must be 0.

    to_lookup = 128 - 128*(1-0) = 0  ∈ [0,127] ✓  (just fits)
    """
    pin, vin = _witness("edge_128_black")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


def test_edge_pixel_0_is_white(binarize_circuit, tmp_path):
    """
    Pixel value 0 (fully bright / pure white).  bin_image must be 1.

    to_lookup = 0  ∈ [0,127] ✓
    """
    pin, vin = _witness("edge_0_white")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


def test_edge_pixel_255_is_black(binarize_circuit, tmp_path):
    """
    Pixel value 255 (fully dark / pure black).  bin_image must be 0.

    to_lookup = 255 - 128 = 127  ∈ [0,127] ✓  (just fits at the high end)
    """
    pin, vin = _witness("edge_255_black")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=True,
                     proof_path=tmp_path / "proof.pi")


def test_edge_127_claimed_black_fails(binarize_circuit, tmp_path):
    """
    Pixel value 127 claimed as black (bin_image=0) — wrong side of threshold.

    to_lookup = 127 - 128*(1-0) = -1  NOT in [0,127] → fails.
    """
    pin, vin = _witness("edge_127_claimed_black")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")


def test_edge_128_claimed_white_fails(binarize_circuit, tmp_path):
    """
    Pixel value 128 claimed as white (bin_image=1) — wrong side of threshold.

    to_lookup = 128 - 128*(1-1) = 128  NOT in [0,127] → fails.
    """
    pin, vin = _witness("edge_128_claimed_white")
    prove_and_verify(pin, vin, binarize_circuit, expect_valid=False,
                     proof_path=tmp_path / "proof.pi")
