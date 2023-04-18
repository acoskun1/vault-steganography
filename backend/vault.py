#!/usr/bin/env python3
from jpeg import JPG, loadJPEG, writeToFile, printMCU
from lsbhide import LSBHide
from lsbreveal import LSBReveal
from datetime import datetime
from dateutil import tz
import argparse
import os
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vault-logger')

start_time = time.time()

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
    _epilog_string = f' Last executed at: {_exec_at:%m/%d/%Y - %H:%M:%S, %Z%z}'
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

alg_group = parser.add_mutually_exclusive_group(required=True)
alg_group.add_argument('-j', '--jsteg', action='store_true', help='jsteg algorithm to embed/retrieve file')
alg_group.add_argument('-L', '--lsb', action='store_true', help='lsb algorithm to embed/retrieve file')

parser.add_argument('-m', '--meta-data', action='store_true', help='return metadata of JPG image being decoded.')
parser.add_argument('cover_image', action='store', metavar='COVER IMAGE', nargs='?', default=None, type=str, help='Path to cover image file [for --embed only]')
parser.add_argument('text_file', action='store',metavar='TEXT FILE', nargs='?', default=None, type=str, help='Path to text file [for --embed only]')
parser.add_argument('stego_image', action='store',metavar='STEGO IMAGE', type=str, help='Path to stego image file [for --embed | --retrieve]')

args = parser.parse_args()

if __name__ == "__main__":

    # retrieve mode checks
    if args.retrieve:
        if args.jsteg:
            if args.text_file is not None or args.cover_image is not None:
                parser.error('Only path to stego image can be specified for --retrieve mode')
            elif args.stego_image is None:
                parser.error('Path to stego image not specified. Please specify the path of stego image.')
            elif not os.path.exists(os.path.dirname(args.stego_image)):
                parser.error(f'Path to stego image directory does not exist:\n\n    {os.path.dirname(args.stego_image)}\n\nPlease specify a valid path or directory.')
            elif not os.path.isfile(args.stego_image):
                parser.error(f'Stego image file cannot be located at:\n\n    {args.stego_image}\n\nPlease specify a valid path or stego image.')
            else:
                if args.jsteg:
                    print(f"Recovering file from image {args.stego_image}.")
                    filedata = loadJPEG(args.stego_image)
                    if filedata == None:
                        parser.error(f'{args.stego_image} is not a valid JPEG file.')
                    else:
                        _stego_image = JPG(args.stego_image)
                        if args.meta_data:
                            logger.info(f' Image metadata:\n{str(_stego_image)}\n')
                        
                        _stego_image.recoverHiddenFile()

        if args.lsb:
            print(f"Recovering file from image {args.stego_image}.")
            print(args)
            _stego_image = JPG(args.stego_image)
            if args.meta_data:
                logger.info(f' Image metadata:\n{str(_stego_image)}\n')
            
            _steg = LSBReveal(args.stego_image)
            _steg.reveal(args.text_file)

            # _stego_image.recoverHiddenFile()

    # embed mode checks
    if args.embed:
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
            if args.jsteg:
                print(f"\nEmbedding from {args.text_file} into {args.cover_image}\n")
                filedata = loadJPEG(args.cover_image)
                if filedata == None:
                    parser.error(f'{args.cover_image} is not a valid JPEG file.')
                else:
                    _cover_image = JPG(args.cover_image)
                    if args.meta_data:
                        logger.info(f' Image metadata:\n{str(_cover_image)}\n')

                    _cover_image.inject(args.text_file)
                    _cover_image.saveJPGData(args.stego_image)
                    logger.info(f' Stego image is saved to {args.stego_image}')

            if args.lsb:
                print(f"\nEmbedding from {args.text_file} into {args.cover_image}\n")
                _cover_image = JPG(args.cover_image)
                if args.meta_data:
                    logger.info(f' Image metadata:\n{str(_cover_image)}\n')
                
                _steg = LSBHide(args.cover_image, args.text_file)
                _steg.embed(args.stego_image)
                logger.info(f' Stego image is saved to {args.stego_image}')

                # logger.info(f' Stego image is saved to {args.stego_image}')
                # printMCU(_cover_image.MCUVector[-1])

    _wall_time = round(time.time() - start_time, 2)
    logger.info(get_epilog())
    logger.info(f' Time Elapsed (wall clock): {_wall_time} s')