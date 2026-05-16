#!/usr/bin/env python3

"""
PDF417 Barcode Generator
Generates a PDF417 barcode image with specified rows, columns, and error correction level.
"""

import argparse
import sys
from math import floor

try:
    import pdf417gen
    from PIL import Image
except ImportError as e:
    print(f"Error: Required library not found: {e}")
    print("Install with: pip install pdf417gen pillow")
    sys.exit(1)


def calculate_data_needed(num_rows, num_cols, ec_level):
    """
    Calculate how much data is needed to achieve desired rows/columns.

    Formula from PDF417 spec:
    total_codewords = num_rows × num_cols
    total_codewords = data_codewords + error_correction_codewords + 1 (symbol length descriptor)

    Error correction codewords by level:
    Level 0: 2, Level 1: 4, Level 2: 8, Level 3: 16, Level 4: 32,
    Level 5: 64, Level 6: 128, Level 7: 256, Level 8: 512
    """
    ec_codewords = {0: 2, 1: 4, 2: 8, 3: 16, 4: 32, 5: 64, 6: 128, 7: 256, 8: 512}

    total_codewords = num_rows * num_cols
    k = ec_codewords[ec_level]

    # Subtract error correction codewords and symbol length descriptor
    data_codewords_needed = total_codewords - k - 1

    if data_codewords_needed < 1:
        raise ValueError(
            f"Cannot fit data with {num_rows} rows, {num_cols} columns, and EC level {ec_level}. "
            f"Need at least {k + 1} total codewords, but only have {total_codewords}."
        )

    # In Text Compaction mode, <= 2 characters per codeword
    # Divide by 1.3 to account for switch/latch codes (empirically this seems to give the right number of rows for this data)
    chars_needed = floor((data_codewords_needed * 2) / 1.3)

    return chars_needed, data_codewords_needed


def generate_data_string(length, style="mixed"):
    """
    Generate a valid text string of approximately the given length.

    All generated text uses only characters valid in PDF417 Text Compaction mode:
    - Uppercase letters (A-Z)
    - Lowercase letters (a-z)
    - Digits (0-9)
    - Space and common punctuation

    Args:
        length (int): Approximate length needed
        style (str): Style of text generation
            - 'mixed': Mix of upper, lower, digits (default)
            - 'upper': Uppercase and digits only
            - 'lower': Lowercase and digits only
            - 'alpha': Letters only (mixed case)
            - 'alnum': Letters and numbers, no punctuation

    Returns:
        str: Generated text string
    """

    if style == "upper":
        # Uppercase letters, digits, and space only
        base_text = "PDF417 BARCODE DATA "
        filler = lambda i: f"BLOCK{i:04d} "

    elif style == "lower":
        # Lowercase letters, digits, and space only
        base_text = "pdf417 barcode data "
        filler = lambda i: f"block{i:04d} "

    elif style == "alpha":
        # Letters only, mixed case, no digits
        base_text = "PDF Barcode Data "
        words = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]
        filler = lambda i: f"{words[i % len(words)]} "

    elif style == "alnum":
        # Alphanumeric only, no punctuation
        base_text = "PDF417 Barcode Data "
        filler = lambda i: f"Block{i:04d} "

    else:  # 'mixed' (default)
        # Mix of everything: upper, lower, digits, punctuation
        # Using only punctuation that's valid in Text Compaction mode
        base_text = "PDF417 barcode data: "
        filler = lambda i: f"Block{i:04d} "

    # Fill with generated text to reach desired length
    text = base_text
    counter = 0
    while len(text) < length:
        text += filler(counter)
        counter += 1

    # Trim to exact length and remove trailing space
    return text[:length].strip()


def generate_pdf417_barcode(
    num_rows,
    num_cols,
    ec_level,
    output_filename="pdf417_barcode.png",
    scale=3,
    padding=0,
    text_style="mixed",
    image_width=None,
    image_height=None,
    barcode_width=None,
    barcode_height=None,
):
    """
    Generate a PDF417 barcode with specific rows, columns, and error correction.

    Args:
        num_rows (int): Number of rows (3-90)
        num_cols (int): Number of columns (1-30)
        ec_level (int): Error correction level (0-8)
        output_filename (str): Output image filename
        scale (int): Scale factor for the image (ignored if image/barcode dimensions set)
        padding (int): Padding/quiet zone around barcode in pixels (ignored in canvas mode)
        text_style (str): Style of generated text data
        image_width (int): Exact output canvas width in pixels
        image_height (int): Exact output canvas height in pixels
        barcode_width (int): Target barcode width in pixels (best-fit integer scale)
        barcode_height (int): Target barcode height in pixels (best-fit integer ratio)

    Returns:
        PIL.Image: The generated barcode image
    """

    # Validate parameters according to PDF417 spec
    if num_rows < 3 or num_rows > 90:
        raise ValueError("Number of rows must be between 3 and 90")

    if num_cols < 1 or num_cols > 30:
        raise ValueError("Number of columns must be between 1 and 30")

    if ec_level < 0 or ec_level > 8:
        raise ValueError("Error correction level must be between 0 and 8")

    if padding < 0:
        raise ValueError("Padding must be non-negative")

    # Calculate and generate appropriate data
    chars_needed, data_codewords = calculate_data_needed(num_rows, num_cols, ec_level)
    data = generate_data_string(chars_needed, style=text_style)

    print(f"Generating PDF417 barcode:")
    print(f"  Rows: {num_rows}")
    print(f"  Columns: {num_cols}")
    print(f"  Error Correction Level: {ec_level}")
    print(f"  Text style: {text_style}")
    print(f"  Generated data length: {len(data)} characters")
    print(f"  Estimated data codewords: {data_codewords}")
    print(f"  Sample data: {data[:60]}...")

    # Encode the data
    codes = pdf417gen.encode(data, columns=num_cols, security_level=ec_level)

    canvas_mode = image_width is not None or image_height is not None or \
                  barcode_width is not None or barcode_height is not None

    if canvas_mode:
        if image_width is None or image_height is None:
            raise ValueError("--image-width and --image-height must both be specified in canvas mode")
        if barcode_width is None or barcode_height is None:
            raise ValueError("--barcode-width and --barcode-height must both be specified in canvas mode")

        num_modules = 17 * (num_cols + 4)
        scale = max(1, round(barcode_width / num_modules))
        ratio = max(1, round(barcode_height / (num_rows * scale)))

        barcode = pdf417gen.render_image(codes, scale=scale, ratio=ratio, padding=0)
        bw, bh = barcode.size

        if bw > image_width or bh > image_height:
            raise ValueError(
                f"Rendered barcode ({bw}x{bh}) exceeds canvas ({image_width}x{image_height}). "
                f"Reduce barcode target dimensions or increase canvas size."
            )

        canvas = Image.new("L", (image_width, image_height), color=255)
        paste_x = (image_width - bw) // 2
        paste_y = (image_height - bh) // 2
        canvas.paste(barcode, (paste_x, paste_y))

        print(f"  Scale: {scale}, Ratio: {ratio}")
        print(f"  Rendered barcode size: {bw}x{bh} pixels")
        print(f"  Canvas size: {image_width}x{image_height} pixels")
        print(f"  Barcode offset: ({paste_x}, {paste_y})")
        print(f"  Circuit crop coordinates:")
        print(f"    R_START={paste_y}, R_END={paste_y + bh}")
        print(f"    C_START={paste_x}, C_END={paste_x + bw}")

        canvas.save(output_filename)
        print(f"\nBarcode saved to: {output_filename}")
        print(f"Image size: {image_width}x{image_height} pixels")
        return canvas
    else:
        print(f"  Scale: {scale}")
        print(f"  Padding: {padding} pixels")
        image = pdf417gen.render_image(codes, scale=scale, ratio=3, padding=padding)
        image.save(output_filename)
        print(f"\nBarcode saved to: {output_filename}")
        print(f"Image size: {image.size[0]}x{image.size[1]} pixels")
        return image


def main():
    parser = argparse.ArgumentParser(
        description="Generate a PDF417 barcode with specified parameters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --rows 10 --cols 5 --ec 2
  %(prog)s -r 15 -c 10 -e 4 -o my_barcode.png
  %(prog)s --rows 20 --cols 8 --ec 3 --scale 5 --padding 20
  %(prog)s -r 10 -c 5 -e 2 --text-style upper --padding 0
  %(prog)s -r 15 -c 10 -e 2 --image-width 1080 --image-height 720 --barcode-width 900 --barcode-height 600

Text Styles (all valid in Text Compaction mode):
  mixed:  Mix of upper, lower, digits, punctuation (default)
  upper:  Uppercase and digits only
  lower:  Lowercase and digits only
  alpha:  Letters only (mixed case)
  alnum:  Letters and numbers, no punctuation

Error Correction Levels:
  0: 2 codewords    (minimal, not recommended)
  1: 4 codewords
  2: 8 codewords    (recommended minimum)
  3: 16 codewords
  4: 32 codewords
  5: 64 codewords
  6: 128 codewords
  7: 256 codewords
  8: 512 codewords  (maximum)
        """,
    )

    parser.add_argument(
        "-r", "--rows", type=int, required=True, help="Number of rows (3-90)"
    )
    parser.add_argument(
        "-c", "--cols", type=int, required=True, help="Number of columns (1-30)"
    )
    parser.add_argument(
        "-e", "--ec", type=int, required=True, help="Error correction level (0-8)"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output filename (default: pdf417_<rows>x<cols>_ec<ec>.png)",
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=int,
        default=3,
        help="Scale factor for image size (default: 3)",
    )
    parser.add_argument(
        "-p",
        "--padding",
        type=int,
        default=0,
        help="Padding/quiet zone in pixels (default: 0)",
    )
    parser.add_argument(
        "--text-style",
        type=str,
        default="mixed",
        choices=["mixed", "upper", "lower", "alpha", "alnum"],
        help="Style of generated text data (default: mixed)",
    )
    parser.add_argument(
        "--image-width",
        type=int,
        default=None,
        help="Exact output canvas width in pixels",
    )
    parser.add_argument(
        "--image-height",
        type=int,
        default=None,
        help="Exact output canvas height in pixels",
    )
    parser.add_argument(
        "--barcode-width",
        type=int,
        default=None,
        help="Target barcode width in pixels (best-fit; requires --image-width/height)",
    )
    parser.add_argument(
        "--barcode-height",
        type=int,
        default=None,
        help="Target barcode height in pixels (best-fit; requires --image-width/height)",
    )

    args = parser.parse_args()

    # Generate default output filename if not provided
    output_filename = args.output
    if output_filename is None:
        output_filename = f"pdf417_{args.rows}x{args.cols}_ec{args.ec}.png"

    try:
        generate_pdf417_barcode(
            num_rows=args.rows,
            num_cols=args.cols,
            ec_level=args.ec,
            output_filename=output_filename,
            scale=args.scale,
            padding=args.padding,
            text_style=args.text_style,
            image_width=args.image_width,
            image_height=args.image_height,
            barcode_width=args.barcode_width,
            barcode_height=args.barcode_height,
        )
        print("\n✓ Success!")

    except ValueError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
