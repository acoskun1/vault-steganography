import argparse
import os

# Create the argument parser
parser = argparse.ArgumentParser(description='Steganography tool for embedding or recovering text from an image')

# Add the mutually exclusive options
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--embed', action='store_true', help='Embed text in the image')
group.add_argument('--recover', action='store_true', help='Recover text from the image')

# Add the image file option
parser.add_argument('image_file', metavar='image', type=str, help='Path to the image file')

# Add the text file option (only for --embed)
parser.add_argument('text_file', metavar='text', type=str, nargs='?', help='Path to the text file (only for --embed)')

# Parse the command line arguments
args = parser.parse_args()

print(args)
# # Check if the image file exists
# if not os.path.isfile(args.image_file):
#     parser.error(f"File not found: {args.image_file}")

# # Check if the text file exists (only for --embed)
# if args.embed and not os.path.isfile(args.text_file):
#     parser.error(f"File not found: {args.text_file}")

# # Print the chosen operation and file paths
# if args.embed:
#     print(f"Embedding text in image {args.image_file} using text file {args.text_file}")
# else:
#     print(f"Recovering text from image {args.image_file}")
