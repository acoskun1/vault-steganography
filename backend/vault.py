import argparse
import os


class CustomHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str, indent_increment: int = 2, max_help_position: int = 24, width: int | None = None) -> None:
        self._prog=prog
        self._title = r"""
 __   ___  ______    __  __    __        ______  
/\ \ /  / /\  __ \  /\ \/\ \  /\ \      /\__  _\ 
\ \ \  /  \ \  __ \ \ \ \_\ \ \ \ \____ \/_/\ \/ 
 \ \__/    \ \_\ \_\ \ \_____\ \ \_____\   \ \_\ 
  \/_/      \/_/\/_/  \/_____/  \/_____/    \/_/

Vault.© 2023 By Ali Coskun    
    """
        super().__init__(prog, indent_increment, max_help_position, width)

    def format_help(self, *args, **kwargs):
        help_text = super().format_help()
        return f'{self._title}\n{help_text}'


# Create the argument parser
parser = argparse.ArgumentParser(prog='vault', 
                                 allow_abbrev=False, 
                                 usage='%(prog)s [options] <text_file> <image_file>', 
                                 description='Steganography tool for embedding or recovering text from an image', 
                                 formatter_class=CustomHelpFormatter,
                                 epilog='Thanks for using %(prog)s.')

# Add the mutually exclusive options
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--embed', action='store_true', help='embed text into image')
group.add_argument('--retrieve', action='store_true', help='retrieve text from image')

# Add the image file option
parser.add_argument('image_file', action='store', metavar='image', type=str, nargs=1, help='Path to the image file [--embed, --retrieve]')

# Add the text file option (only for --embed)
parser.add_argument('text_file', action='store',metavar='text', type=str, nargs='?', help='Path to the text file [--embed only]')

# Parse the command line arguments
args = parser.parse_args()

# Check if the image file exists
if not os.path.isfile(args.image_file[0]):
    parser.error(f"Image file is not found: {args.image_file[0]}")

# Check if the text file exists (only for --embed)
if args.embed and not os.path.isfile(args.text_file):
    parser.error(f"File not found: {args.text_file}")

# Print the chosen operation and file paths
if args.embed:
    print(f"Embedding text from {args.text_file} into image {args.image_file[0]}.")
else:
    print(f"Recovering text from image {args.image_file[0]}.")
