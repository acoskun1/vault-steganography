import numpy as np

class BitReader:

    """
    Reads individual bits from byte array. Huffman coded bitstream arrives as a large byte array.
    Huffman coded bitstream compresses the variable length codes, therefore it must be read one bit at a time. 
    We cannot read in fixed size.
    
    + readNextBit(self, n=1): reads the next n bits from the byte array. If n is not specified, taken as 1 by default. 
    """
    def __init__(self, data: bytearray, beginning_byte = np.uint8(0)) -> None:
        self.data = data
        self.byte = np.uint8(beginning_byte)
        self.bit = 0 # the bit read at a time

    def readNextBit(self, n = 1) -> int:
        nbits = np.uint8(0)
        for i in range(n):
            byte = self.data[self.byte]
            lsb_position = 7 - self.bit # used to select the appropriate bit from byte.
            byte >>= lsb_position # shifts to the right to get the LSB of the byte. amount shifted is determined by the bit being read at the time.
            nbits <<=  1 # shifts to the left creating space for next bit to be added.
            nbits |=  (byte & 0x01) # sets the LSB of the nbits to extracted bit.
            self.bit = (self.bit + 1) % 8 # when 8 bits is read, wraps bit to 0 again.
            
            # checks if all 8 bits in the byte have been read
            # increments byte to move to next byte in the bitstream.
            if self.bit == 0:
                self.byte += 1
        return nbits