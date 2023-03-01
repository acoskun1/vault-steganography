import argparse
import os

# Create the argument parser
parser = argparse.ArgumentParser(prog='vault', allow_abbrev=False, description='Steganography tool for embedding or recovering text from an image', epilog='Thanks for using %(prog)s.')

# Add the mutually exclusive options
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-e','--embed', action='store_true', help='embed text into image')
group.add_argument('-r','--recover', action='store_true', help='retrieve text from image')

# Add the image file option
parser.add_argument('image_file', action='store' ,metavar='image', type=str, help='Path to the image file')

# Add the text file option (only for --embed)
parser.add_argument('text_file', action='store',metavar='text', type=str, nargs='?', help='Path to the text file (only for --embed)')
parser.add_argument()
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
