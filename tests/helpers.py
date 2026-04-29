"""
Utility functions shared across all ZoKrates circuit test modules.

Import these in test files:
    from helpers import compile_and_setup, prove_and_verify, ZOK_DIR, WITNESSES_DIR
"""

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CIRC_DIR = REPO_ROOT / "external" / "circ"
ZOK_DIR = REPO_ROOT / "zokrates"
BIN_DIR = ZOK_DIR / "bin"
SCRIPTS_DIR = REPO_ROOT / "python-scripts"
WITNESSES_DIR = REPO_ROOT / "tests" / "witnesses"

# CirC requires this env var to find the SMT solver (mirrors generate-proof.sh)
CIRC_ENV = {**os.environ, "RSMT2_CVC4_CMD": "cvc5"}

# Ristretto/Curve25519 scalar field modulus — required by the dorian proof system
# (matches MOD in python-scripts/json_to_witness.py)
DORIAN_MOD = "7237005577332262213973186563042994240857116359379907606001950938285454250989"


def json_to_witness(witness: dict, json_path: Path) -> tuple[Path, Path]:
    """
    Write *witness* dict to *json_path* and run json_to_witness.py to produce
    a .pin and .vin alongside it.  Returns (pin_path, vin_path).

    Typical usage with pytest's tmp_path fixture:
        pin, vin = json_to_witness(w, tmp_path / "mytest.json")
    """
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(witness))

    pin_path = json_path.with_suffix(".pin")
    vin_path = json_path.with_suffix(".vin")

    result = subprocess.run(
        [
            "python",
            str(SCRIPTS_DIR / "json_to_witness.py"),
            "-i", str(json_path),
            "--pin", str(pin_path),
            "--vin", str(vin_path),
            "--modulus", DORIAN_MOD,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"json_to_witness.py failed for {json_path.name}:\n{result.stderr}"
        )

    return pin_path, vin_path


def compile_and_setup(zok_path: Path, skip: bool = False) -> str:
    """
    Compile *zok_path* with CirC and generate prover/verifier keys.

    - *skip=True* and keys exist  → skip compilation, return basename.
    - *skip=True* and keys missing → raise RuntimeError.
    - *skip=False*                 → always compile.

    Returns the circuit basename (e.g. ``'binarize'``).
    """
    basename = zok_path.stem
    prover_key = BIN_DIR / f"{basename}_P"
    verifier_key = BIN_DIR / f"{basename}_V"
    BIN_DIR.mkdir(exist_ok=True)

    if skip:
        if not prover_key.exists() or not verifier_key.exists():
            raise RuntimeError(
                f"--no-setup passed but keys for '{basename}' not found in {BIN_DIR}. "
                "Run without --no-setup first to compile the circuit."
            )
        return basename

    # Build the CirC binary if it doesn't exist yet
    circ_bin = CIRC_DIR / "target" / "release" / "examples" / "circ"
    if not circ_bin.exists():
        build = subprocess.run(
            ["python", "driver.py", "-b"],
            cwd=str(CIRC_DIR),
            capture_output=True,
            text=True,
            env=CIRC_ENV,
        )
        if build.returncode != 0:
            raise RuntimeError(f"CirC build failed:\n{build.stderr}")

    result = subprocess.run(
        [
            str(circ_bin),
            str(zok_path),
            "--language", "zsharp-curly",
            "r1cs",
            "--action", "setup",
            "--proof-impl", "dorian",
            "--prover-key", str(prover_key),
            "--verifier-key", str(verifier_key),
        ],
        cwd=str(CIRC_DIR),
        capture_output=True,
        text=True,
        env=CIRC_ENV,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"CirC setup failed for {zok_path.name}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    return basename


def prove_and_verify(
    pin_path: Path,
    vin_path: Path,
    basename: str,
    expect_valid: bool = True,
    proof_path: Path | None = None,
) -> None:
    """
    Run prove then verify for a compiled circuit.

    - *expect_valid=True*:  asserts prove and verify both succeed.
    - *expect_valid=False*: asserts prove fails OR verify rejects the proof.

    Pass an explicit *proof_path* (e.g. inside tmp_path) when running tests
    in parallel to avoid different tests overwriting each other's proof file.
    """
    if proof_path is None:
        proof_path = BIN_DIR / f"{basename}.pi"

    zk_bin = CIRC_DIR / "target" / "release" / "examples" / "zk"

    prove = subprocess.run(
        [
            str(zk_bin),
            "--action", "prove",
            "--proof-impl", "dorian",
            "--prover-key", str(BIN_DIR / f"{basename}_P"),
            "--inputs", str(pin_path),
            "--proof", str(proof_path),
        ],
        cwd=str(CIRC_DIR),
        capture_output=True,
        text=True,
        env=CIRC_ENV,
    )

    if not expect_valid:
        if prove.returncode != 0:
            return  # correctly rejected at prove stage
        verify = subprocess.run(
            [
                str(zk_bin),
                "--action", "verify",
                "--proof-impl", "dorian",
                "--verifier-key", str(BIN_DIR / f"{basename}_V"),
                "--inputs", str(vin_path),
                "--proof", str(proof_path),
            ],
            cwd=str(CIRC_DIR),
            capture_output=True,
            text=True,
            env=CIRC_ENV,
        )
        assert verify.returncode != 0, (
            "Expected proof to be INVALID but verify accepted it.\n"
            f"prove stdout: {prove.stdout}\n"
            f"verify stdout: {verify.stdout}"
        )
        return

    assert prove.returncode == 0, (
        "Expected prove to SUCCEED but it failed.\n"
        f"stdout: {prove.stdout}\nstderr: {prove.stderr}"
    )
    verify = subprocess.run(
        [
            str(zk_bin),
            "--action", "verify",
            "--proof-impl", "dorian",
            "--verifier-key", str(BIN_DIR / f"{basename}_V"),
            "--inputs", str(vin_path),
            "--proof", str(proof_path),
        ],
        cwd=str(CIRC_DIR),
        capture_output=True,
        text=True,
        env=CIRC_ENV,
    )
    assert verify.returncode == 0, (
        "Expected verify to SUCCEED but it failed.\n"
        f"stdout: {verify.stdout}\nstderr: {verify.stderr}"
    )
