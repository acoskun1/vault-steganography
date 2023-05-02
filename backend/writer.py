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
    + write_int(self, i, len) -> None:
        Takes integer and length, writes the length least significant bits of i to the data array.
    + copy(self, data) -> None:
        Takes an array of integers.
        Copies the contents of the data array.
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
    
    def write_int(self, i: int, len: int) -> None:
        for j in range(len):
            self.write(bool((i >> len - j - 1) & 0x01))
    
    def copy(self, data: List[int]) -> None:
        for i in self.data_:
            data.append(i)
            if i == 0xFF:
                data.append(0x00)