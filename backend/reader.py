from typing import List
import numpy as np

class BitReader:

    """
    Reads each bit from the binary data.

    + readNextBit(self, n=1): reads the next n bits from the secret data and returns the result. If n is not specified, taken as 1 by default.
        If n > number of remaining bits, return remaining bits.
        If no remaining bits, return 0. 
    + isRead(self): sets self.read to true if bits in data is read.
    """
    def __init__(self, data: List[np.uint8], beginning_byte = np.uint8(0)) -> None:
        self.data = data
        self.byte = np.uint8(beginning_byte)
        self.Bit = 0
        self.isread = False

    def readNextBit(self, n = 1) -> int:
        res = np.uint8(0)
        byte = None
        for i in range(n):
            if self.isread:
                break
            byte = self.data[self.byte]
            byte = byte >> (7 - self.Bit)
            res <<=  1
            res = res | (byte & 0x01)

            self.Bit = (self.Bit + 1) % 8
            if self.Bit == 0:
                self.byte += 1

            if self.byte >= len(self.data):
                self.isread = True
        return res

    def isRead(self) -> bool:
        return self.isread