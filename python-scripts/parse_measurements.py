import os
import re
import csv

MEASUREMENTS_DIR = os.path.join(os.path.dirname(__file__), "../zokrates/for-measurement/measurements")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "../zokrates/for-measurement/measurements.csv")

COLUMNS = [
    "circuit", "image_rows", "image_cols", "barcode_rows", "barcode_cols",
    "max_rows", "max_cols", "max_ec_level", "chunk_size",
    "prover_time_1", "prover_time_2", "prover_time_3", "prover_time_4", "prover_time_5",
    "prover_ram_1", "prover_ram_2", "prover_ram_3", "prover_ram_4", "prover_ram_5",
    "verifier_time_1", "verifier_time_2", "verifier_time_3", "verifier_time_4", "verifier_time_5",
    "verifier_ram_1", "verifier_ram_2", "verifier_ram_3", "verifier_ram_4", "verifier_ram_5",
]

def parse_file(path):
    with open(path) as f:
        text = f.read()

    def meta(key):
        m = re.search(rf"^{key}:\s+(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else None

    circuit_raw = meta("circuit")
    if not circuit_raw:
        return None
    circuit = re.sub(r"^bench_", "", circuit_raw)

    image = meta("image")
    barcode_actual = meta("barcode_actual")
    if not image or not barcode_actual:
        return None

    img_cols, img_rows = map(int, image.split("x"))
    bar_cols, bar_rows = map(int, barcode_actual.split("x"))

    max_rows = meta("max_rows")
    max_cols = meta("max_cols")
    max_ec_level = meta("max_ec_level")
    chunk_size = meta("chunk_size")

    prover_times = re.findall(r"Time for Proving \(commit\): ([\d.]+)ms", text)
    verifier_times = re.findall(r"Time for NIZK::verify_commit: ([\d.]+)ms", text)

    prove_rams = []
    verify_rams = []

    sections = re.split(r"=== (prove|verify) iteration \d+ ===", text)
    i = 1
    while i + 1 < len(sections):
        kind = sections[i]
        body = sections[i + 1]
        ram_m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", body)
        if ram_m:
            ram = int(ram_m.group(1))
            if kind == "prove":
                prove_rams.append(ram)
            else:
                verify_rams.append(ram)
        i += 2

    if (len(prover_times) != 5 or len(verifier_times) != 5 or
            len(prove_rams) != 5 or len(verify_rams) != 5):
        return None

    row = {
        "circuit": circuit,
        "image_rows": img_rows,
        "image_cols": img_cols,
        "barcode_rows": bar_rows,
        "barcode_cols": bar_cols,
        "max_rows": max_rows,
        "max_cols": max_cols,
        "max_ec_level": max_ec_level,
        "chunk_size": chunk_size,
    }
    for i, v in enumerate(prover_times, 1):
        row[f"prover_time_{i}"] = round(float(v), 2)
    for i, v in enumerate(prove_rams, 1):
        row[f"prover_ram_{i}"] = v
    for i, v in enumerate(verifier_times, 1):
        row[f"verifier_time_{i}"] = round(float(v), 2)
    for i, v in enumerate(verify_rams, 1):
        row[f"verifier_ram_{i}"] = v

    return row


rows = []
skipped = 0

for bench_dir in sorted(os.listdir(MEASUREMENTS_DIR)):
    dir_path = os.path.join(MEASUREMENTS_DIR, bench_dir)
    if not os.path.isdir(dir_path) or not bench_dir.startswith("bench_"):
        continue
    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(dir_path, fname)
        row = parse_file(fpath)
        if row is None:
            skipped += 1
        else:
            rows.append(row)

with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
print(f"Skipped {skipped} incomplete files")
