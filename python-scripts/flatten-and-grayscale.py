#!/usr/bin/env python3

"""
Image to Grayscale Array Converter
Converts an image to a flattened array of grayscale pixel values (0-255).
"""

import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    print("Error: PIL/Pillow library not found.")
    print("Install it with: pip install pillow")
    sys.exit(1)


def image_to_grayscale_array(image_path):
    """
    Convert an image to a flattened grayscale array.

    Args:
        image_path (str): Path to the input image

    Returns:
        list: Flattened array of pixel values (0-255)
    """

    # Load the image
    img = Image.open(image_path)

    # Convert to grayscale
    img_gray = img.convert("L")

    # Convert to array and flatten
    pixel_array = np.array(img_gray).flatten()

    # Convert to Python list
    return pixel_array.tolist()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python image_to_array.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]

    try:
        pixel_array = image_to_grayscale_array(image_path)
        print(pixel_array)

    except FileNotFoundError:
        print(f"Error: Image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
