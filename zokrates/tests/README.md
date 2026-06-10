# ZK Barcodes — Circuit Test Suite

Python + pytest test suite that compiles ZoKrates circuits with CirC and
verifies proofs using the Dorian proof system.

---

## Directory layout

```
tests/
  conftest.py               pytest hooks (--no-setup flag)
  helpers.py                shared utilities: compile_and_setup, prove_and_verify
  test_binarize.py          binarize circuit tests

  zok_wrappers/             thin .zok files with test-sized parameters
    test_binarize.zok       imports binarize(), sets R=4, C=8

  witnesses/
    generate_binarize.py    builds .pin/.vin files for all binarize tests
    binarize/               pre-generated witness files (one per test)
      happy_all_dark.pin/.vin
      cheat_dark_as_white.pin/.vin
      ...
```

---

## Quick start

```bash
# Step 1 — generate witness files (run once, or after changing params)
python tests/witnesses/generate_binarize.py

# Step 2 — compile circuit and run tests
pytest tests/test_binarize.py

# Step 3 (subsequent runs) — skip recompile if keys already exist
pytest tests/test_binarize.py --no-setup
```

---

## Running a subset of tests

```bash
pytest tests/test_binarize.py -k "happy"   # happy-path tests only
pytest tests/test_binarize.py -k "cheat"   # cheating tests only
pytest tests/test_binarize.py -k "edge"    # edge-case tests only

pytest tests/test_binarize.py::test_cheat_dark_pixel_claimed_white  # one test
```

---

## How to change parameters

Each circuit has two places where parameters live — they must be kept in sync:

| File | What to change |
|---|---|
| `tests/zok_wrappers/test_<circuit>.zok` | `const u32` values (read by CirC at compile time) |
| `tests/witnesses/generate_<circuit>.py` | matching Python variables at the top of the file |

After changing parameters:
1. Edit both files.
2. Regenerate witnesses: `python tests/witnesses/generate_<circuit>.py`
3. Recompile and test: `pytest tests/test_<circuit>.py` (without `--no-setup`)

---

## binarize parameters

**Wrapper:** `tests/zok_wrappers/test_binarize.zok`

| Parameter | Default | Meaning |
|---|---|---|
| `R` | `4` | Number of image rows |
| `C` | `8` | Number of image columns |

**Constraints on values:**
- `R >= 1`, `C >= 2` (mixed witness splits columns in half)
- Larger values increase compile and prove time substantially

**Example — change to 8×16:**

In `tests/zok_wrappers/test_binarize.zok`:
```zokrates
const u32 R = 8;
const u32 C = 16;
```

In `tests/witnesses/generate_binarize.py`:
```python
R, C = 8, 16
```

Then regenerate and retest:
```bash
python tests/witnesses/generate_binarize.py
pytest tests/test_binarize.py
```

---

## How two-phase testing works

**Phase 1 — compile (slow, cached)**

`pytest tests/test_binarize.py` compiles the wrapper `.zok` with CirC and
writes prover/verifier keys to `zokrates/bin/`. This only needs to happen
when the circuit or its parameters change.

**Phase 2 — prove/verify (fast)**

Each test loads pre-generated `.pin`/`.vin` files and runs `zk prove` +
`zk verify` against the cached keys. This is fast enough to run on every
change.

Use `--no-setup` to skip Phase 1 when keys already exist:
```bash
pytest tests/test_binarize.py --no-setup
```

---

## Adding a new circuit test suite

1. Add `tests/zok_wrappers/test_<circuit>.zok` — import the circuit function
   and provide a `main()` with small test-sized constants.
2. Add `tests/witnesses/generate_<circuit>.py` — construct witnesses for each
   test case and call `json_to_witness()` to write `.pin`/`.vin` files.
3. Add `tests/test_<circuit>.py` — load witnesses with `_witness("name")` and
   call `prove_and_verify(..., expect_valid=True/False)`.
4. Run `python tests/witnesses/generate_<circuit>.py` then
   `pytest tests/test_<circuit>.py`.
