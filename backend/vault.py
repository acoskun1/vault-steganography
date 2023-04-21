#!/usr/bin/env python3
from jpeg import JPG, loadJPEG, printMCU
from datetime import datetime
from dateutil import tz
import argparse
import os
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vault-logger')

start_time = time.time()

# custom help formatter generated using an ASCII art. Does not have an impact on the steganography and steganalysis schemes.
class CustomHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog: str, indent_increment: int = 2, max_help_position: int = 24, width: int | None = None) -> None:
        self._prog=prog
        self._title = r"""
 __   ___  ______    __  __    __        ______  
/\ \ /  / /\  __ \  /\ \/\ \  /\ \      /\__  _\ 
\ \ \  /  \ \  __ \ \ \ \_\ \ \ \ \____ \/_/\ \/ 
 \ \__/    \ \_\ \_\ \ \_____\ \ \_____\   \ \_\ 
  \/_/      \/_/\/_/  \/_____/  \/_____/    \/_/

Vault. v1.0 Apr 2023 By Ali Coskun    
    """
        super().__init__(prog, indent_increment, max_help_position, width)

    def format_help(self, *args, **kwargs):
        help_text = super().format_help()
        return f'{self._title}\n{help_text}'

# returns the last time executed.
def get_epilog() -> str:
    _exec_at = datetime.now(tz=tz.UTC)
    _epilog_string = f' Last executed at: {_exec_at:%m/%d/%Y - %H:%M:%S, %Z%z}'
    return _epilog_string

parser = argparse.ArgumentParser(prog='vault', 
                                 allow_abbrev=False,
                                 usage='%(prog)s [options] <path_to_cover_image> <path_to_secret_file> <path_to_stego_image>', 
                                 description='Steganography tool for embedding or recovering secret file from/into a JPG image.', 
                                 formatter_class=CustomHelpFormatter,
                                 epilog= get_epilog())

# mutually exclusive group, can either use --embed or --retrieve one at a time.
mode_group = parser.add_mutually_exclusive_group(required=True)
mode_group.add_argument('--embed', action='store_true', help='embed file into image')
mode_group.add_argument('--retrieve', action='store_true', help='retrieve file from image')

parser.add_argument('-m', '--meta-data', action='store_true', help='return metadata of JPG image being decoded.')
parser.add_argument('cover_image', action='store', metavar='COVER IMAGE', nargs='?', default=None, type=str, help='Path to cover image file [for --embed only]')
parser.add_argument('secret_file', action='store',metavar='SECRET FILE', nargs='?', default=None, type=str, help='Path to secret file [for --embed only]')
parser.add_argument('stego_image', action='store',metavar='STEGO IMAGE', type=str, help='Path to stego image file [for --embed | --retrieve]')

args = parser.parse_args()

if __name__ == "__main__":

    # retrieve mode checks
    if args.retrieve:
        # retrieve mode only accepts path to stego image. if cover image or secret file is specified, throws error.
        if args.secret_file is not None or args.cover_image is not None:
                parser.error('Only path to stego image can be specified for --retrieve mode')
        # checks if path to stego image is provided.
        elif args.stego_image is None:
                parser.error('Path to stego image not specified. Please specify the path of stego image.')
        # checks if path to stego image exists.
        elif not os.path.exists(os.path.dirname(args.stego_image)):
                parser.error(f'Path to stego image directory does not exist:\n\n    {os.path.dirname(args.stego_image)}\n\nPlease specify a valid path or directory.')
        # checks if stego file exists in the path.
        elif not os.path.isfile(args.stego_image):
                parser.error(f'Stego image file cannot be located at:\n\n    {args.stego_image}\n\nPlease specify a valid path or stego image.')
        else:
            print(f"Recovering file from image {args.stego_image}.")
            # checks if stego image is JPEG and loads file data.
            filedata = loadJPEG(args.stego_image)
            if filedata == None:
                parser.error(f'{args.stego_image} is not a valid JPEG file.')
            else:
                # decodes the stego image by creating a JPG.
                _stego_image = JPG(args.stego_image)
                # if --meta-data option is selected, returns metadata of decoded JPG
                if args.meta_data:
                    logger.info(f' Image metadata:\n{str(_stego_image)}\n')              
                
                # retrieving the secret message happens here
                _stego_image.recoverHiddenFile()
                logger.info(f' Secret file is saved to current working directory. Type ls to see file.')



    # embed mode checks
    if args.embed:
        
        # checks if no path to cover image is specified
        if args.cover_image is None:
            parser.error('Path to cover image is not specified. Please specify the path of cover image.')
        # checks if the path to cover image exists
        elif not os.path.exists(os.path.dirname(args.cover_image)):
            parser.error(f'Path to cover image directory does not exist:\n\n    {os.path.dirname(args.cover_image)}\n\nPlease specify a valid path or directory.')
        # checks if file exists in the path
        elif not os.path.isfile(args.cover_image):
            parser.error(f'Cover image file cannot be located at:\n\n    {args.cover_image}\n\nPlease specify a valid path and image.')
        
        # checks if no path to secret file is specified
        elif args.secret_file is None:
            parser.error('Path to text file is not specified.')
        # checks if path to file exists
        elif not os.path.exists(os.path.dirname(args.secret_file)):
            parser.error(f'Path to text file directory does not exist:\n\n    {os.path.dirname(args.secret_file)}\n\nPlease specify a valid path or directory.')
        # checks if file exists in the path
        elif not os.path.isfile(args.secret_file):
            parser.error(f'Text file cannot be located at:\n\n    {args.secret_file}\n\nPlease specify a valid path or text file.')
        
        # checks if path to stego image is specified
        elif args.stego_image is None:
            parser.error('Path to save the stego image is not specified.')
        # checks if path to where stego image is going to be written exists
        elif not os.path.exists(os.path.dirname(args.stego_image)):
            parser.error(f'Path to stego image directory does not exist:\n\n    {os.path.dirname(args.stego_image)}\n\nPlease specify a valid path or directory.')
        # if image exists in the path, throw error. It does not allow overwriting.
        elif os.path.isfile(args.stego_image):
            parser.error(f'An image already exists at:\n\n    {args.stego_image}\n\nCannot override image, please specify a different path or name.')
        else:
            print(f"\nEmbedding from {args.secret_file} into {args.cover_image}\n")
            # checks if the cover image is actually JPEG and loads file data.
            filedata = loadJPEG(args.cover_image)
            if filedata == None:
                parser.error(f'{args.cover_image} is not a valid JPEG file.')
            else:
                # decoding begins by initialising JPG object using cover image
                _cover_image = JPG(args.cover_image)
                # if --meta-data flag is passed, returns summary of decoded cover image.
                if args.meta_data:
                    logger.info(f' Image metadata:\n{str(_cover_image)}\n')
                
                # hiding secret file to cover image begins here. 
                _cover_image.inject(args.secret_file)
                # saves the new jpeg data (post injection) to at stego image.
                _cover_image.saveJPGData(args.stego_image)
                logger.info(f' Stego image is saved to {args.stego_image}')

                # printMCU(_cover_image.MCUVector[-1])

    # not steganography related. returns the wall clock time.
    _wall_time = round(time.time() - start_time, 2)
    logger.info(get_epilog())
    logger.info(f' Time Elapsed (wall clock): {_wall_time} s')