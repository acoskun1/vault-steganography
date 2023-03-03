from datetime import datetime
from dateutil import tz
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

def get_epilog() -> str:
    _exec_at = datetime.now(tz=tz.UTC)
    _epilog_string = f'Executed at: {_exec_at:%m/%d/%Y - %H:%M:%S, %Z%z}'
    return _epilog_string

parser = argparse.ArgumentParser(prog='vault', 
                                 allow_abbrev=False, 
                                 usage='%(prog)s [options] <path_to_cover_image> <path_to_text_file> <path_to_stego_image>', 
                                 description='Steganography tool for embedding or recovering secret text from/into a JPG image.', 
                                 formatter_class=CustomHelpFormatter,
                                 epilog= get_epilog())

mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument('--embed', action='store_true', help='embed text into image')
mode_group.add_argument('--retrieve', action='store_true', help='retrieve text from image')

parser.add_argument('cover_image', action='store', metavar='COVER IMAGE', type=str, help='Path to cover image file [for --embed only]')
parser.add_argument('text_file', action='store',metavar='TEXT FILE', type=str, help='Path to text file [for --embed only]')
parser.add_argument('stego_image', action='store',metavar='STEGO IMAGE', type=str, help='Path to stego image file [for --embed | --retrieve]')

args = parser.parse_args()
print(args)

# retrieve mode checks
if args.retrieve:
    if args.stego_image is None:
        parser.error('Path to stego image not specified.')
    elif not os.path.isfile(args.stego_image):
        parser.error(f'Stego image file cannot be located at:\n\n    {args.stego_image}\n')

# embed mode checks
if args.embed:
    if args.cover_image is None:
        parser.error('Path to cover image is not specified.')
    elif args.text_file is None:
        parser.error('Path to text file is not specified.')
    elif args.stego_image is None:
        parser.error('Path to stego image is not specified.')
    elif not os.path.isfile(args.text_file):
        parser.error(f"Text file cannot be located at:\n\n    {args.text_file}")
    elif not os.path.isfile(args.cover_image):
        parser.error(f"Cover image file cannot be located at:\n\n    {args.cover_image[0]}")
    elif os.path.isfile(args.stego_image):
        parser.error('File already exists, please choose a different directory, or name.')

if args.embed and os.path.isfile(args.cover_image) and os.path.isfile(args.text_file) and args.stego_image:
    print(f"Embedding text from {args.text_file} into image {args.cover_image} at {args.stego_image}")
else:
    print(f"Recovering text from image {args.stego_image}.")

print(get_epilog())