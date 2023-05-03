from typing import List

class BitWriter:
    """
    Write bits one at a time to data array.
    + __init__(self) -> None: 
        Constructor method for the BitWriter class. Sets the initial value of the next_bit_ member to 0.
    + write_bit(bit) -> None:
        writes individual bit to the last byte always.
        takes the last byte by accessing index [-1] at bytestream.
    + write_code(self, i, len) -> None:
        Used for writing codes to the bitstream.
        i: integer, len: length of code.
    + add(self, data) -> None:
        Takes a bytearray and adds the contents of self.data_ into the bytearray.
        Adds a 0x00 after each 0xFF byte to avoid conflicts with JPEG marker segments.
        In the huffman coded bitstream, 0xFF bytes are free to appear.
    """
    # BitWriter and BitReader are implemented because, Huffman coded bitstream shows variable lengths
    # We cannot read fixed sizes, therefore we must read and write bit at a time.
    
    def __init__(self) -> None:
        self.data_ = [] # stores the byte array contents.
        self.next_bit_ = 0

    # writes an integer to the bitstream. i = integer, len = length of the integer.
    # used for writing codes to the bitstream.
    def write_code(self, i: int, len: int) -> None:
        # iterates length times, shifts i to the right by len - j - 1 and checks if LSB is 1 by setting the result of bitwise AND 0x01 to boolean
        for j in range(len):
            #if 1, calls write_bool()
            self.write_bit((i >> len - j - 1) & 0x01)   

    # writes individual bits by using boolean arbitrary. If true -> 1, if false -> 0
    def write_bit(self, bit: int) -> None:

        if self.next_bit_ == 0:
            self.data_.append(0x00)
        
        # if bit is 1, sets the appropriate bit in the last byte of data_.
        # to get the last byte, chooses [-1] all times.
        if bit:
            last_byte = self.data_[-1]
            lsb_position = (7 - self.next_bit_) # gets the least significant bit position of the byte

            last_byte |= (bit << lsb_position) # sets the lsb position in last byte to 1.
            self.data_[-1] = last_byte
        
        self.next_bit_ = (self.next_bit_ + 1) % 8 # used to wrap the value of next bit to 0 when 8th bit is reached.
    
    def add(self, data: bytearray) -> None:
        for i in self.data_:
            data.append(i) # adds contents of self.data_
            if i == 0xFF: # when 0xFF is encountered, adds 0x00 to avoid conflicts with JPEG marker segments normally starting with 0xFF byte.
                data.append(0x00)