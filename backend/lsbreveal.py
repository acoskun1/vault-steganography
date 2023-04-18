from PIL import Image
from stegano import lsb
import numpy as np
import logging

# import numpy as np

# img = np.array(Image.open('images/wall.jpg'))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vault-logger')

class LSBReveal:
    def __init__(self, stego_image) -> None:
        self.image_file_ = stego_image
        self.text_: str = ''


    def reveal(self, revealed_text_write_location) -> None:
        try:
            self.text_ = lsb.reveal(self.image_file_)

            with open(revealed_text_write_location, 'w') as text_file:
                text_file.write(self.text_)

            logger.info(f' Reveal successful. Text saved to {revealed_text_write_location}')

        except Exception as exception:
            logger.error(f' Reveal failed. {exception}')