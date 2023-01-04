#!/usr/bin/env python3

from struct import unpack

import sys
import numpy as np


"""Stores the markers in a map"""
markermap = {
    0xffd8: "SOI",
    0xffe0: "APP0",
    0xffe1: "APP1",
    0xffdb: "DQT",
    0xffc0: "SOF",
    0xffc4: "DHT",
    0xffda: "SOS",
    0xffd9: "EOI"
}

"""
There are different quantisation table standards for luminance and chroma channels.
"""

class JPEG:
    def __init__(self, file):
        with open(file, 'rb') as f:
            self.img_data = f.read()

    def decode(self):
        data = self.img_data
        while(True):
            marker, = unpack(">H", data[0:2])
            print(markermap.get(marker))
            if marker == 0xffd8:
                data = data[2:]
            elif marker == 0xffd9:
                return
            elif marker == 0xffda:
                data = data[-2:]
            else:
                lenchunk, = unpack(">H", data[2:4])
                data = data[2+lenchunk:]            
            if len(data)==0:
                break   


if __name__ == "__main__":
    img = JPEG('bolt.jpg')
    img.decode()    