from typing import List
import numpy as np

class BitReader:

    """
    Reads individual bits from binary data'

    + next(self, n=1): reads the next n bits from the data and returns the result.
        If n is greater than the number of remaining bits, only the remaining bits will be returned
        If there are no more remaining bits, 0 will be returned. 

    + read(self): returns a bool indicating if all bits in data have been read.
    
    + skipToNextByte(self): skips rest of the bits in the current byte and starts the next read operation
    from the most significant (MSB) bit of the next byte.
    """
    #matt passes the data with reference ??
    def __init__(self, data: List[np.uint8], startByte = np.uint8(0)) -> None:
        self.data_ = data
        self.currByte_ = np.uint8(startByte)
        self.currBit_ = 0
        self.read_ = False

    def readNextBit(self, n = 1) -> int:
        result = np.uint8(0)
        currByte = None
        for i in range(n):
            if self.read_:
                break
            currByte = self.data_[self.currByte_]
            currByte = currByte >> (7 - self.currBit_)
            result = result << 1
            result = result | (currByte & 0x01)

            self.currBit_ = (self.currBit_ + 1) % 8
            if self.currBit_ == 0:
                self.currByte_ += 1

            if self.currByte_ >= len(self.data_):
                self.read_ = True
        return result

    def isRead(self) -> bool:
        return self.read_

    def skipByte(self) -> None:
        if self.currByte_ != len(self.data_) - 1:
            self.currByte_ += 1
            self.currBit_ = 0