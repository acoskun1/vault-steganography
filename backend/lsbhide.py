from PIL import Image
from stegano import lsb
import numpy as np
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vault-logger')

class LSBHide:
    def __init__(self, image_carrier, secret_text) -> None:
        self.image_file = image_carrier
        self.text_file = secret_text


    def embed(self, stego_image_write_location) -> None:
        try:
            with open(self.text_file, 'r') as text_file:
                secret_text = text_file.read()

            stego = lsb.hide(self.image_file, secret_text)
            stego.save(stego_image_write_location)

            print(lsb.reveal(stego_image_write_location))

            logger.info(f' Hiding successful. Stego image saved to {stego_image_write_location}')

        except Exception as exception:
            logger.error(f' Hidding unsuccessful. {exception}')