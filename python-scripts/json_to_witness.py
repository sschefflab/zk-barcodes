#!/usr/bin/env python3
"""
Generic JSON to witness file converter for ZoKrates/CirC.

Converts a JSON file into .pin (prover input) and .vin (verifier input) files
in S-expression format for use with CirC's ZK tooling.

Type detection:
  - Booleans (true/false) → bool
  - Integers → field (default) or u32 if specified
  - Strings starting with '#' → passed through as-is

Type hints (optional):
  - Use "_types" object to specify types: {"image": "u32", "count": "field"}
  - Use "_public" array to specify public inputs: ["digest", "commitment"]
  - Use "_return" to specify return values for .vin file

Examples:
  # Simple case - auto-detect types
  python json_to_witness.py -i data.json -o witness

  # With explicit mapping for field names
  python json_to_witness.py -i witness.json -o binarize \\
      --map image=image --map bin_image=binarized_image
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

MOD = "52435875175126190479447740508185965837690552500527637822603658699938581184513"


def format_field_value(value: Union[int, str]) -> str:
    """Format a value as a field element in decimal."""
    if isinstance(value, str):
        if value.startswith("#"):
            return value
        value = int(value, 0)
    return f"#f{value}"


def format_u32_value(value: Union[int, str]) -> str:
    """Format a value as a u32 in hex."""
    if isinstance(value, str):
        if value.startswith("#"):
            return value
        value = int(value, 0)
    return f"#x{value:08x}"


def format_bool_value(value: Union[bool, int, str]) -> str:
    """Format a boolean value."""
    if isinstance(value, str):
        value = value.lower() in ("true", "1", "yes")
    elif isinstance(value, int):
        value = bool(value)
    return "true" if value else "false"


def infer_type(value: Any) -> str:
    """Infer the type of a value."""
    if isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "field"  # default for integers
    elif isinstance(value, str):
        if value.startswith("#x"):
            return "u32"
        elif value.startswith("#f"):
            return "field"
        elif value.lower() in ("true", "false"):
            return "bool"
        return "field"
    elif isinstance(value, list):
        if len(value) > 0:
            return infer_type(value[0])
        return "field"
    return "field"


def format_value(value: Any, value_type: str) -> str:
    """Format a value according to its type."""
    if value_type == "bool":
        return format_bool_value(value)
    elif value_type == "u32":
        return format_u32_value(value)
    else:  # field
        return format_field_value(value)


def flatten_value(
    prefix: str, value: Any, type_hints: Dict[str, str]
) -> List[Tuple[str, str]]:
    """
    Recursively flatten a value into (name, formatted_value) pairs.

    Args:
        prefix: The current path prefix (e.g., "image" or "stats.ec_level")
        value: The value to flatten
        type_hints: Type hints for specific paths

    Returns:
        List of (name, formatted_value) tuples
    """
    entries = []

    # Get type hint for this path, or infer from value
    value_type = type_hints.get(prefix, infer_type(value))

    if isinstance(value, dict):
        # Recursively handle nested objects
        for key, val in value.items():
            if key.startswith("_"):  # Skip metadata keys
                continue
            child_prefix = f"{prefix}.{key}" if prefix else key
            entries.extend(flatten_value(child_prefix, val, type_hints))
    elif isinstance(value, list):
        # Handle arrays
        for i, item in enumerate(value):
            child_prefix = f"{prefix}.{i}"
            # Check for per-element type hint, fallback to array type hint
            child_type = type_hints.get(
                child_prefix, type_hints.get(prefix, infer_type(item))
            )

            if isinstance(item, (dict, list)):
                entries.extend(flatten_value(child_prefix, item, type_hints))
            else:
                entries.append((child_prefix, format_value(item, child_type)))
    else:
        # Scalar value
        entries.append((prefix, format_value(value, value_type)))

    return entries


def write_witness_file(
    entries: List[Tuple[str, str]], output_path: str, modulus: Optional[str] = None
):
    """Write entries to a witness file in S-expression format."""
    with open(output_path, "w") as f:
        if modulus:
            f.write(f"(set_default_modulus {modulus}\n")
        f.write("(let (\n")
        for name, value in entries:
            f.write(f"    ({name} {value})\n")
        f.write(") true\n)\n")
        if modulus:
            f.write(")\n")
    print(f"Generated {output_path} ({len(entries)} entries)")


def apply_mappings(data: Dict, mappings: Dict[str, str]) -> Dict:
    """
    Apply field name mappings to create a new data dict.

    Args:
        data: Original JSON data
        mappings: Dict of {output_name: input_name}

    Returns:
        New dict with mapped field names
    """
    if not mappings:
        return data

    result = {}
    for out_name, in_name in mappings.items():
        if in_name in data:
            result[out_name] = data[in_name]
        else:
            print(f"Warning: '{in_name}' not found in input data", file=sys.stderr)

    # Include unmapped fields if no explicit mappings for them
    for key, value in data.items():
        if key not in result and not key.startswith("_"):
            # Check if this key is used as a source in mappings
            if key not in mappings.values():
                result[key] = value

    return result


def parse_type_hints(data: Dict) -> Dict[str, str]:
    """Extract type hints from the _types field."""
    type_hints = {}
    if "_types" in data:
        for path, type_name in data["_types"].items():
            type_hints[path] = type_name
    return type_hints


def main():
    parser = argparse.ArgumentParser(
        description="Convert JSON to ZoKrates/CirC witness files (.pin/.vin)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  %(prog)s -i data.json -o witness

  # Map JSON field names to ZoKrates parameter names
  %(prog)s -i witness.json -o binarize --map image=image --map bin_image=binarized_image

  # Specify types explicitly
  %(prog)s -i data.json -o witness --type digest=u32 --type image=field

  # Mark fields as public (included in .vin)
  %(prog)s -i data.json -o witness --public digest --public commitment

  # Limit array size (useful for testing with smaller N)
  %(prog)s -i witness.json -o test --map image=image --limit image=32

Type detection:
  - true/false → bool
  - integers → field (default)
  - Use --type to override (e.g., --type digest=u32)

The _types, _public, and _return fields in JSON are also recognized.
        """,
    )

    parser.add_argument("-i", "--input", required=True, help="Input JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default="witness",
        help="Output basename (creates .pin and .vin)",
    )
    parser.add_argument("--pin", help="Override .pin output path")
    parser.add_argument("--vin", help="Override .vin output path")
    parser.add_argument(
        "--map",
        action="append",
        metavar="OUT=IN",
        help="Map output field name to input field name (repeatable)",
    )
    parser.add_argument(
        "--type",
        action="append",
        metavar="FIELD=TYPE",
        help="Set type for a field: field, u32, bool (repeatable)",
    )
    parser.add_argument(
        "--public",
        action="append",
        metavar="FIELD",
        help="Mark field as public (included in .vin)",
    )
    parser.add_argument(
        "--limit",
        action="append",
        metavar="FIELD=N",
        help="Limit array field to first N elements (repeatable)",
    )
    parser.add_argument(
        "--only-pin", action="store_true", help="Only generate .pin file"
    )
    parser.add_argument(
        "--only-vin", action="store_true", help="Only generate .vin file"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="FIELD",
        help="Exclude field from output (repeatable)",
    )
    parser.add_argument(
        "--modulus", metavar="MODULUS", help="Set field modulus (required for Spartan)"
    )
    parser.add_argument(
        "--default-mod",
        action="store_true",
        help="Use default modulus (shorthand for --modulus 5243587517...)",
    )

    args = parser.parse_args()

    # Handle modulus
    modulus = None
    if args.default_mod:
        modulus = MOD
    elif args.modulus:
        modulus = args.modulus

    # Load input JSON
    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    # Parse field mappings
    mappings = {}
    if args.map:
        for m in args.map:
            if "=" not in m:
                print(
                    f"Error: Invalid mapping '{m}', expected OUT=IN format",
                    file=sys.stderr,
                )
                sys.exit(1)
            out_name, in_name = m.split("=", 1)
            mappings[out_name] = in_name

    # Parse type hints from command line
    type_hints = parse_type_hints(data)
    if args.type:
        for t in args.type:
            if "=" not in t:
                print(
                    f"Error: Invalid type '{t}', expected FIELD=TYPE format",
                    file=sys.stderr,
                )
                sys.exit(1)
            field, type_name = t.split("=", 1)
            if type_name not in ("field", "u32", "bool"):
                print(
                    f"Error: Unknown type '{type_name}', expected field/u32/bool",
                    file=sys.stderr,
                )
                sys.exit(1)
            type_hints[field] = type_name

    # Parse limits
    limits = {}
    if args.limit:
        for l in args.limit:
            if "=" not in l:
                print(
                    f"Error: Invalid limit '{l}', expected FIELD=N format",
                    file=sys.stderr,
                )
                sys.exit(1)
            field, n = l.split("=", 1)
            limits[field] = int(n)

    # Apply limits to data
    for field, n in limits.items():
        source_field = mappings.get(field, field)
        if source_field in data and isinstance(data[source_field], list):
            data[source_field] = data[source_field][:n]

    # Apply mappings
    if mappings:
        # Only include mapped fields when explicit mappings are provided
        mapped_data = {}
        for out_name, in_name in mappings.items():
            if in_name in data:
                mapped_data[out_name] = data[in_name]
            else:
                print(f"Warning: '{in_name}' not found in input data", file=sys.stderr)
        data = mapped_data

    # Remove excluded fields
    if args.exclude:
        for field in args.exclude:
            data.pop(field, None)

    # Remove metadata fields
    for key in list(data.keys()):
        if key.startswith("_"):
            del data[key]

    # Parse public fields
    public_fields = set(data.get("_public", []))
    if args.public:
        public_fields.update(args.public)

    # Flatten all data
    all_entries = []
    for key, value in data.items():
        all_entries.extend(flatten_value(key, value, type_hints))

    # Separate public and private entries
    public_entries = []
    private_entries = []
    for name, value in all_entries:
        # Check if this entry or its parent is public
        is_public = False
        for pub_field in public_fields:
            if name == pub_field or name.startswith(f"{pub_field}."):
                is_public = True
                break

        if is_public:
            public_entries.append((name, value))
        private_entries.append((name, value))  # .pin includes everything

    # Handle return values for .vin
    if "_return" in data:
        return_entries = flatten_value("return", data["_return"], type_hints)
        public_entries.extend(return_entries)

    # Determine output paths
    pin_path = args.pin if args.pin else f"{args.output}.pin"
    vin_path = args.vin if args.vin else f"{args.output}.vin"

    # Generate files
    if not args.only_vin:
        write_witness_file(all_entries, pin_path, modulus)

    if not args.only_pin:
        if public_entries:
            write_witness_file(public_entries, vin_path, modulus)
        else:
            print(f"Note: No public fields specified, .vin file will be empty")
            write_witness_file([], vin_path, modulus)

    print(f"\nUsage with CirC:")
    print(f"  cd external/circ")
    if modulus:
        print(f"  ./target/release/examples/zk --field-custom-modulus {modulus} \\")
        print(f"      --pin ../../{pin_path} --vin ../../{vin_path} --action spartan")
    else:
        print(
            f"  ./target/release/examples/zk --inputs ../../{pin_path} --action prove"
        )


if __name__ == "__main__":
    main()
