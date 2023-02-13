from typing import List

class BitWriter:

    """
    Write bits one at a time to data array.

    + __init__(self) -> None: 
        Constructor method for the BitWriter class. Sets the initial value of the nextBit_ member to 0.
    + write(bit) -> None:
        If nextBit_ is 0, new byte is added to the data vector. 
        If bit is True, last byte in the data array is set to have its least significant bit set to 1. 
        nextBit_ is then updated to point to the next bit to be written.

    + write_byte(self, c) -> None:
        Writes each of i's 8 bits to the data array.
        If nextBit_ is 0, the entire integer is added to the data vector as a new byte.
        If nextBit_ is not 0, each bit of c is written using the write(bit) function

    + write_int(self, i, len) -> None:
        Takes integer and length, writes the length least significant bits of i to the data array.
    
    + copy(self, data, ) -> None:
        Takes an array of integers and a boolean addPadding argument.
        Copies the contents of the data array.
        If addPadding True, adds padding bits to the end of the data vector.

    + pad(self, bit=False) -> None:
        Takes an optional boolean 'bit' argument and pads the data array with 0 or 1 bits depending on the value of 'bit'
    """

    def __init__(self) -> None:
        self.data_ = []
        self.nextBit_ = 0
    
    def write(self, bit: bool) -> None:
        if self.nextBit_ == 0:
            self.data_.append(0x00)
        
        if bit:
            self.data_[-1] = self.data_[-1] >> (7 - self.nextBit_)
            self.data_[-1] = self.data_[-1] | 0x01
            self.data_[-1] = self.data_[-1] << (7 - self.nextBit_)
        
        self.nextBit_ = (self.nextBit_ + 1) % 8
    
    def write_byte(self, i: int) -> None:
        if self.nextBit_ == 0:
            self.data_.append(i)
        else:
            for j in range(8):
                b = (i >> (7 - j)) & 0x01
                self.write(b)
    
    def write_int(self, i: int, len: int) -> None:
        for j in range(len):
            self.write(bool((i >> len - j - 1) & 0x01))
    
    def copy(self, data: List[int]) -> None:
        for i in self.data:
            data.append(i)
            if i == 0xFF:
                data.append(0x00)
    
    def pad(self, bit = False) -> None:
        if bit:
            while self.nextBit > 0:
                self.write(True)
        else:
            self.nextBit = 0
