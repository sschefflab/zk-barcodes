#!/usr/bin/env python3
"""
Generate .pin and .vin files for zokrates/main.zok

This script creates witness files in S-expression format for the ZoKrates main circuit.
Inputs can be provided as JSON files.

Modify the constants below to match your ZoKrates circuit parameters.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Union

# ============================================================================
# CIRCUIT CONSTANTS - Modify these to match your ZoKrates program
# ============================================================================
N = 32  # Image size (must be divisible by 16 for SHA256)
D = 16  # Number of blocks
W = 2   # Number of words

# Derived constants (computed from above)
SHA_OUTPUT_SIZE = 8
SHA_BLOCK_SIZE = 16
SHA_NUM_BLOCKS = N // SHA_BLOCK_SIZE
CHAR_TABLE_SIZE = 2 * W
RETURN_SIZE = 2 * W
# ============================================================================


def format_field_value(value: Union[int, str]) -> str:
    """Format a value as a field element in hex."""
    if isinstance(value, str):
        if value.startswith('#'):
            return value
        value = int(value, 0)
    return f"#f{value:x}"


def format_u32_value(value: Union[int, str]) -> str:
    """Format a value as a u32 in hex."""
    if isinstance(value, str):
        if value.startswith('#'):
            return value
        value = int(value, 0)
    return f"#x{value:08x}"


def format_bool_value(value: Union[bool, int, str]) -> str:
    """Format a boolean value."""
    if isinstance(value, str):
        value = value.lower() in ('true', '1', 'yes')
    return 'true' if value else 'false'


def format_struct_row_indicator_vars(data: Dict) -> List[tuple]:
    """Format RowIndicatorVars struct fields."""
    fields = ['l0', 'l3', 'l6', 'q0', 'q3', 'q6', 'r0', 'r3']
    return [(f"row_indc.{field}", format_field_value(data[field])) for field in fields]


def format_struct_barcode_stats(data: Dict) -> List[tuple]:
    """Format BarcodeStats struct fields."""
    fields = ['ec_level', 'num_rows', 'num_cols']
    return [(f"stats.{field}", format_field_value(data[field])) for field in fields]


def format_struct_table_state(data: Dict, index: int) -> List[tuple]:
    """Format TableState struct fields."""
    fields = ['base30_val', 'char', 'this_table', 'next_table', 'next_next_table']
    prefix = f"char_table_states.{index}"
    return [(f"{prefix}.{field}", format_field_value(data[field])) for field in fields]


def format_struct_polynomial_witness(data: Dict, index: int) -> List[tuple]:
    """Format PolynomialWitness<W> struct fields."""
    prefix = f"poly_witness.{index}"
    result = []

    # Arrays of size W
    for i, coeff in enumerate(data['coeffs'][:W]):
        result.append((f"{prefix}.coeffs.{i}", format_field_value(coeff)))

    result.append((f"{prefix}.eval_point", format_field_value(data['eval_point'])))

    for i, power in enumerate(data['powers'][:W]):
        result.append((f"{prefix}.powers.{i}", format_field_value(power)))

    for i, pq in enumerate(data['powers_quotients'][:W]):
        result.append((f"{prefix}.powers_quotients.{i}", format_field_value(pq)))

    for i, term in enumerate(data['terms'][:W]):
        result.append((f"{prefix}.terms.{i}", format_field_value(term)))

    for i, tq in enumerate(data['terms_quotients'][:W]):
        result.append((f"{prefix}.terms_quotients.{i}", format_field_value(tq)))

    return result


def generate_pin_file(data: Dict, output_path: str):
    """Generate the .pin file (prover inputs - all inputs)."""
    entries = []

    # PUBLIC: image_digest (u32[SHA_OUTPUT_SIZE])
    for i, val in enumerate(data['image_digest'][:SHA_OUTPUT_SIZE]):
        entries.append((f"image_digest.{i}", format_u32_value(val)))

    # PRIVATE: image (field[N])
    for i, val in enumerate(data['image'][:N]):
        entries.append((f"image.{i}", format_field_value(val)))

    # PRIVATE: image_u32 (u32[SHA_NUM_BLOCKS][SHA_BLOCK_SIZE])
    for block_idx, block in enumerate(data['image_u32'][:SHA_NUM_BLOCKS]):
        for word_idx, val in enumerate(block[:SHA_BLOCK_SIZE]):
            entries.append((f"image_u32.{block_idx}.{word_idx}", format_u32_value(val)))

    # PRIVATE: bin_image (bool[N])
    for i, val in enumerate(data['bin_image'][:N]):
        entries.append((f"bin_image.{i}", format_bool_value(val)))

    # PRIVATE: transitions (bool[N])
    for i, val in enumerate(data['transitions'][:N]):
        entries.append((f"transitions.{i}", format_bool_value(val)))

    # PRIVATE: counts (field[D])
    for i, val in enumerate(data['counts'][:D]):
        entries.append((f"counts.{i}", format_field_value(val)))

    # PRIVATE: normalized_blocks (field[W][8])
    for i, block in enumerate(data['normalized_blocks'][:W]):
        for j, val in enumerate(block[:8]):
            entries.append((f"normalized_blocks.{i}.{j}", format_field_value(val)))

    # PRIVATE: words_with_dummies (field[W])
    for i, val in enumerate(data['words_with_dummies'][:W]):
        entries.append((f"words_with_dummies.{i}", format_field_value(val)))

    # PRIVATE: codewords (field[W])
    for i, val in enumerate(data['codewords'][:W]):
        entries.append((f"codewords.{i}", format_field_value(val)))

    # PRIVATE: corrected_codewords (field[W])
    for i, val in enumerate(data['corrected_codewords'][:W]):
        entries.append((f"corrected_codewords.{i}", format_field_value(val)))

    # PRIVATE: poly_witness (PolynomialWitness<W>[512])
    for i, pw in enumerate(data['poly_witness']):
        entries.extend(format_struct_polynomial_witness(pw, i))

    # PRIVATE: stats (BarcodeStats)
    entries.extend(format_struct_barcode_stats(data['stats']))

    # PRIVATE: row_indc (RowIndicatorVars)
    entries.extend(format_struct_row_indicator_vars(data['row_indc']))

    # PRIVATE: char_table_states (TableState[CHAR_TABLE_SIZE])
    for i, ts in enumerate(data['char_table_states'][:CHAR_TABLE_SIZE]):
        entries.extend(format_struct_table_state(ts, i))

    # Write the .pin file
    with open(output_path, 'w') as f:
        f.write("(let (\n")
        for name, value in entries:
            f.write(f"    ({name} {value})\n")
        f.write(")\n    false\n)\n")

    print(f"Generated {output_path}")


def generate_vin_file(data: Dict, output_path: str):
    """Generate the .vin file (verifier inputs - public inputs and outputs only)."""
    entries = []

    # PUBLIC: image_digest (u32[SHA_OUTPUT_SIZE])
    for i, val in enumerate(data['image_digest'][:SHA_OUTPUT_SIZE]):
        entries.append((f"image_digest.{i}", format_u32_value(val)))

    # PUBLIC OUTPUT: return value (field[RETURN_SIZE], since 2*W)
    if 'return' in data:
        for i, val in enumerate(data['return'][:RETURN_SIZE]):
            entries.append((f"return.{i}", format_field_value(val)))

    # Write the .vin file
    with open(output_path, 'w') as f:
        f.write("(let (\n")
        for name, value in entries:
            f.write(f"    ({name} {value})\n")
        f.write(")\n    false\n)\n")

    print(f"Generated {output_path}")


def load_json_file(path: str) -> Dict:
    """Load data from a JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def create_default_data() -> Dict:
    """Create a template data structure with dummy values."""
    return {
        'image_digest': [0] * SHA_OUTPUT_SIZE,
        'image': [0] * N,
        'image_u32': [[0] * SHA_BLOCK_SIZE for _ in range(SHA_NUM_BLOCKS)],
        'bin_image': [False] * N,
        'transitions': [False] * N,
        'counts': [0] * D,
        'normalized_blocks': [[0] * 8 for _ in range(W)],
        'words_with_dummies': [0] * W,
        'codewords': [0] * W,
        'corrected_codewords': [0] * W,
        'poly_witness': [
            {
                'coeffs': [0] * W,
                'eval_point': 0,
                'powers': [0] * W,
                'powers_quotients': [0] * W,
                'terms': [0] * W,
                'terms_quotients': [0] * W,
            }
            for _ in range(512)
        ],
        'stats': {
            'ec_level': 0,
            'num_rows': 0,
            'num_cols': 0,
        },
        'row_indc': {
            'l0': 0, 'l3': 0, 'l6': 0,
            'q0': 0, 'q3': 0, 'q6': 0,
            'r0': 0, 'r3': 0,
        },
        'char_table_states': [
            {
                'base30_val': 0,
                'char': 0,
                'this_table': 0,
                'next_table': 0,
                'next_next_table': 0,
            }
            for _ in range(CHAR_TABLE_SIZE)
        ],
        'return': [0] * RETURN_SIZE,  # For .vin file
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate .pin and .vin files for zokrates/main.zok',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Current constants (modify at top of script):
  N = {N} (image size)
  D = {D} (number of blocks)
  W = {W} (number of words)

  Derived: SHA_NUM_BLOCKS={SHA_NUM_BLOCKS}, CHAR_TABLE_SIZE={CHAR_TABLE_SIZE}

Examples:
  # Generate template with current constants
  %(prog)s --template -o template.json

  # Generate from JSON file
  %(prog)s -i witness_data.json -o output

  # Generate with specific output paths
  %(prog)s -i data.json --pin custom.pin --vin custom.vin

Note: If you change N, D, or W in your ZoKrates program, update the constants
at the top of this script before generating files.
        """
    )

    parser.add_argument(
        '-i', '--input',
        help='Input JSON file with witness data'
    )
    parser.add_argument(
        '-o', '--output',
        default='witness',
        help='Output basename (will create .pin and .vin files). Default: witness'
    )
    parser.add_argument(
        '--pin',
        help='Output path for .pin file (overrides -o)'
    )
    parser.add_argument(
        '--vin',
        help='Output path for .vin file (overrides -o)'
    )
    parser.add_argument(
        '--template',
        action='store_true',
        help='Generate a template JSON file with dummy values'
    )

    args = parser.parse_args()

    # Validate N is divisible by 16
    if N % 16 != 0:
        print(f"Error: N ({N}) must be divisible by 16 for SHA256 blocks", file=sys.stderr)
        print("Update the N constant at the top of this script.", file=sys.stderr)
        sys.exit(1)

    # Handle template generation
    if args.template:
        template_data = create_default_data()
        output_file = args.output if args.output.endswith('.json') else f"{args.output}.json"
        with open(output_file, 'w') as f:
            json.dump(template_data, f, indent=2)

        print(f"Generated template file: {output_file}")
        print(f"\nCurrent constants: N={N}, D={D}, W={W}")
        print(f"Derived: SHA_NUM_BLOCKS={SHA_NUM_BLOCKS}, CHAR_TABLE_SIZE={CHAR_TABLE_SIZE}")
        print("\nEdit this file with your witness values and run:")
        print(f"  {sys.argv[0]} -i {output_file} -o output")
        return

    if not args.input:
        parser.error("Either --input or --template is required")

    # Load witness data
    try:
        data = load_json_file(args.input)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output paths
    pin_path = args.pin if args.pin else f"{args.output}.pin"
    vin_path = args.vin if args.vin else f"{args.output}.vin"

    # Generate files
    try:
        print(f"Using constants: N={N}, D={D}, W={W}")
        print(f"Derived: SHA_NUM_BLOCKS={SHA_NUM_BLOCKS}, CHAR_TABLE_SIZE={CHAR_TABLE_SIZE}")
        generate_pin_file(data, pin_path)
        generate_vin_file(data, vin_path)
        print("\nSuccess! You can now use these files with circ:")
        print(f"  cd external/circ")
        print(f"  ./target/release/examples/zk --inputs ../../{pin_path} --action prove")
        print(f"  ./target/release/examples/zk --inputs ../../{vin_path} --action verify")
    except KeyError as e:
        print(f"Error: Missing required field in input data: {e}", file=sys.stderr)
        print("\nGenerate a template to see the required structure:")
        print(f"  {sys.argv[0]} --template -o template.json")
        sys.exit(1)
    except (IndexError, ValueError) as e:
        print(f"Error: Data size mismatch. Check that your data matches the constants.", file=sys.stderr)
        print(f"Expected: N={N}, D={D}, W={W}")
        print(f"Error details: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating witness files: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
