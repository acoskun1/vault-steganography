#!/usr/bin/env python3
from jpeg import JPG, loadJPEG, printMCU
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
    _epilog_string = f'Last executed at: {_exec_at:%m/%d/%Y - %H:%M:%S, %Z%z}'
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

if __name__ == "__main__":
    # retrieve mode checks
    if args.retrieve == True:
        if args.stego_image is None:
            parser.error('Path to stego image not specified. Please specify the path of stego image.')
        elif not os.path.exists(os.path.dirname(args.stego_image)):
            parser.error(f'Path to stego image directory does not exist:\n\n    {os.path.dirname(args.stego_image)}\n\nPlease specify a valid path or directory.')
        elif not os.path.isfile(args.stego_image):
            parser.error(f'Stego image file cannot be located at:\n\n    {args.stego_image}\n\nPlease specify a valid path or stego image.')
        
        elif args.text_file is None:
            parser.error(f'Path to extract text file is not specified. Please specify the path to which text file will be saved.')
        elif not os.path.exists(os.path.dirname(args.text_file)):
            parser.error(f'Path to extract text file does not exist: {os.path.dirname(args.text_file)}')
        elif os.path.isfile(args.text_file):
            parser.error('Text file already exists. Cannot overwrite, please specify a different name or path.')

        elif args.cover_image is None:
            parser.error('Path to extract image file is not specified. Please specify the path to which cover image will be saved.')
        elif not os.path.exists(os.path.dirname(args.cover_image)):
            parser.error(f'Path to extract image file does not exist:\n\n   {os.path.dirname(args.cover_image)}\n')
        elif os.path.isfile(args.cover_image):
            parser.error(f'Image file already exists, please specify a different path or name')
        else:
            print(f"Recovering text from image {args.stego_image}.")

    # embed mode checks
    if args.embed == True:
        if args.cover_image is None:
            parser.error('Path to cover image is not specified. Please specify the path of cover image.')
        elif not os.path.exists(os.path.dirname(args.cover_image)):
            parser.error(f'Path to cover image directory does not exist:\n\n    {os.path.dirname(args.cover_image)}\n\nPlease specify a valid path or directory.')
        elif not os.path.isfile(args.cover_image):
            parser.error(f'Cover image file cannot be located at:\n\n    {args.cover_image}\n\nPlease specify a valid path and image.')

        elif args.text_file is None:
            parser.error('Path to text file is not specified.')
        elif not os.path.exists(os.path.dirname(args.text_file)):
            parser.error(f'Path to text file directory does not exist:\n\n    {os.path.dirname(args.text_file)}\n\nPlease specify a valid path or directory.')
        elif not os.path.isfile(args.text_file):
            parser.error(f'Text file cannot be located at:\n\n    {args.text_file}\n\nPlease specify a valid path or text file.')


        elif args.stego_image is None:
            parser.error('Path to save the stego image is not specified.')
        elif not os.path.exists(os.path.dirname(args.stego_image)):
            parser.error(f'Path to stego image directory does not exist:\n\n    {os.path.dirname(args.stego_image)}\n\nPlease specify a valid path or directory.')
        elif os.path.isfile(args.stego_image):
            parser.error(f'An image already exists at:\n\n    {args.stego_image}\n\nCannot override image, please specify a different path or name.')
        else:
            print(f"Embedding text from {args.text_file} into image at {args.cover_image}\nStego image is saved to {args.stego_image}\n")
            filedata = loadJPEG(args.cover_image)
            if filedata == None:
                parser.error(f'{args.cover_image} is not a valid JPEG file.')
            else:
                _cover_image = JPG(args.cover_image)
                # printMCU(_cover_image.MCUVector[-1])
    print(get_epilog())