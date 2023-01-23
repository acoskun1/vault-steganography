#!/usr/bin/env python3

from struct import unpack
from typing import List
import os
import sys
import numpy as np

#Markers that are supported for JPEG
supportedMarkers = {
    0xD8: 'Start of Image (SOI)',
    0xE0: 'JFIF segment marker (APP0)',
    0xE1: 'EXIF segment marker (APP1)',
    0xDB: 'Define Quantisation Table (DQT)',
    0xC0: 'Start of Frame (SOF)',
    0xC4: 'Define Huffman Table (DHT)',
    0xDA: 'Start of Scan (SOS)',
    0xD9: 'End of Image (EOI)'
}

#Markers that are not supported for JPEG
unsupportedMarkers = {
    0xC1: 'Extended Sequential DCT',
    0xC2: 'Progressive DCT',
    0xC3: 'Lossless',
    0xC5: 'Differential Sequential DCT',
    0xC6: 'Differential Progressive DCT',
    0xC7: 'Differential Lossless',
    0xC9: 'Extended Sequential DCT',
    0xCA: 'Progressive DCT',
    0xCB: 'Lossless (Sequential)',
    0xCD: 'Differential Sequential DCT',
    0xCE: 'Differential Progressive DCT',
    0xCF: 'Differential Lossless',
    0xCC: 'Arithmetic Coding',
    0x01: 'TEM Marker - Arithmetic Coding'
}

class Header:
    def __init__(self) -> None:
        self.startOfFrame = StartOfFrame()
        self.startOfScan = StartOfScan()
        self.components = [Component() for i in range(3)] #list comprehension - creating new Component object on each iteration and appends to the list (Y'CbCr)
        self.dcHuffmanTables = [HuffmanTable() for i in range(2)]
        self.acHuffmanTables = [HuffmanTable() for i in range(2)]
        self.bitstreamIndex = 0
        self.restartInterval = 0
        self.quantizationTables = []
        self.app0Marker = []

    def readSOS(self, data: List[int], start: int, length: int) -> None:
        i = start + 2
        current = data[i]

        if current != self.startOfFrame.numOfComponents:
            raise Exception('Error - Wrong number of components in Start of Scan.')
        
        componentId = None
        for j in range(self.startOfFrame.numOfComponents):
            component = self.components[j]
            componentId = data[i+1]
            if componentId != component.identifier:
                raise Exception('Error - Wrong Component ID in Start of Scan.')
            component.dcHuffmanTableId = data[i+2] >> 4
            component.acHuffmanTableId = data[i+2] & 0x0F
            i += 1

        i += 3
        if i != start + length - 1:
            raise Exception('Error - Number of bytes do not equal the length of marker.')
        self.startOfScan.set = True        

    def addSOS(self, data: List[int]) -> None:
        data.append(0xFF)
        data.append(0xDA)
        data.append(0x00)
        data.append((6 + (2 * self.startOfFrame.numOfComponents)) & 0xff)
        data.append(self.startOfFrame.numOfComponents)

        for i in range(self.startOfFrame.numOfComponents):
            data.append(self.components[i].identifier)
            j = (self.components[i].dcHuffmanTableId << 4) | self.components[i].acHuffmanTableId
            data.append(j & 0xff)
        
        data.append(0x00)
        data.append(0x00)
        data.append(0x00)
        
    def readSOF(self, data: List[int], start: int, length: int) -> None:
        i = start + 2

        if data[i] != 0x08:
            raise Exception('Invalid precision.')
        self.startOfFrame.precision = data[i]
        
        #Image Height
        self.startOfFrame.height = self.startOfFrame.height + (data[i+1] << 8)
        i += 1
        self.startOfFrame.height = self.startOfFrame.height + data[i+1]
        i += 1

        #Image Width
        self.startOfFrame.width = self.startOfFrame.width + (data[i+1] << 8)
        i += 1
        self.startOfFrame.width = self.startOfFrame.width + data[i+1]
        i += 1

        i += 1
        if data[i] != 0x01 and data[i] != 0x03:
            raise Exception('Invalid number of components.')
        self.startOfFrame.numOfComponents = data[i]

        for _ in range(self.startOfFrame.numOfComponents):
            comp = self.components[_]
            comp.identifier = data[i+1]
            i += 1
            comp.horizontalSamplingFactor = data[i+1] >> 4
            comp.verticalSamplingFactor = data[i+1] & 0x0F
            i += 1
            comp.quantizationTableNumber = data[i+1]
            i += 1
        
        if self.startOfFrame.numOfComponents > 1:
            if ((self.components[0].verticalSamplingFactor != 1 and self.components[0].verticalSamplingFactor != 2)
            or (self.components[0].horizontalSamplingFactor != 1 and self.components[0].horizontalSamplingFactor != 2)
            or (self.components[1].horizontalSamplingFactor != 1 or self.components[1].verticalSamplingFactor != 1)
            or (self.components[2].horizontalSamplingFactor != 1 or self.components[2].verticalSamplingFactor != 1)):
                raise Exception('Error - Invalid sampling factor.')
        else:
            self.components[0].verticalSamplingFactor = 1
            self.components[0].horizontalSamplingFactor = 1
            
        if i != start + length - 1:
            raise Exception('Incorrect Start of Frame length.')
        self.startOfFrame.set = True

    def addSOF(self, data: List[int]) -> None:
        data.append(0xFF)
        data.append(0xC0)
        data.append(0x00)
        
        if self.startOfFrame.numOfComponents == 1:
            data.append(0x0B)
        else:
            data.append(0x11)
        
        data.append(0x08)
        data.append((self.startOfFrame.height >> 8) & 0xFF)
        data.append((self.startOfFrame.height) & 0xFF)
        data.append((self.startOfFrame.width >> 8) & 0xFF)
        data.append((self.startOfFrame.width) & 0xFF)
        data.append(self.startOfFrame.numOfComponents & 0xFF)

        for i in range(self.startOfFrame.numOfComponents):
            c = (self.components[i].horizontalSamplingFactor & 0x0F) << 4
            c = c | (self.components[i].verticalSamplingFactor & 0x0F)
            data.append(self.components[i].identifier & 0xFF)

            data.append(c)
            data.append(self.components[i].quantizationTableNumber & 0xFF)

    def readHT(self, data: List[int], start: int, length: int):
        hufftable = None
        curr = 0
        i = start + 2

        while i < (start + length):
            curr = data[i]
            if (curr >> 4) > 1:
                raise ValueError('Error - Wrong Class')
            
            if (curr & 0x0F) > 1:
                raise ValueError('Error- Wrong Destination')

            if (curr >> 4) == 0:
                hufftable = self.dcHuffmanTables[curr & 0x0F]
            else:
                hufftable = self.acHuffmanTables[curr & 0x0F]

            if hufftable.set:
                raise ValueError('Error - Multiple Huffman Tables')

            total = 0
            for j in range(1,17):
                total += data[i+1]
                hufftable.offsets[j] = total
                i += 1

            for j in range(total):
                hufftable.symbols[j] = data[i+1]
                i += 1
            hufftable.set = True
            self.getHuffmanCodes(hufftable)
            i += 1

    def readQT(self, data: List[int], start: int, length: int):
        self.quantizationTables.append(0xFF)
        self.quantizationTables.append(0xDB)

        for i in range(start, length):
            self.quantizationTables.append(data[i])

    def readRI(self, data: List[int], start: int, length: int) -> None:
        i  = start + 2

        if length != 4:
            raise ValueError('Error - Wrong length of Restart Interval Marker')
        
        self.restartInterval =  self.restartInterval
        

class StartOfFrame:
    def __init__(self) -> None:
        self.precision = 0
        self.height = 0
        self.width = 0
        self.numOfComponents = 0x00
        self.set = False

#Component Class (Y'CbCr or Grayscale)
class Component:
    def __init__(self) -> None:
        self.identifier = 0
        self.quantizationTableNumber = 0
        self.acHuffmanTableId = 0
        self.dcHuffmanTableId = 0
        self.verticalSamplingFactor = 0
        self.horizontalSamplingFactor = 0

#Colour Channel Class
class Channel:
    def __init__(self) -> None:
        self.dcCoeff = 0            #DC coefficient of pixel block
        self.acCoeff = [0] * 63     #AC coefficients of pixel block

#Huffman Table Class (Multiple Tables in single JPEG)
class HuffmanTable:
    def __init__(self) -> None:
        self.symbols = [0x00]*162
        self.offsets = [0]*17
        self.codes = [0]*162
        self.set = False

class StartOfScan:
    def __init__(self) -> None:
        self.set = False

class MCU:
    def __init__(self) -> None:
        self.luminance = [Channel() for i in range (4)]
        self.chrominance = [Channel() for i in range(2)]
        
class JPG:
    def __init__(self, file):
        self.img_data = self.readJPG(file)


    #Input file JPG format validator.
    def readJPG(self, file):
        try:         
            with open(file, 'rb') as f:
                header = f.read(4)
                marker, = unpack(">H", header[0:2])
                if marker not in supportedMarkers:
                    raise ValueError('Invalid JPEG file')
                return f.read()
        except FileNotFoundError:
            print('Error - Cannot open input file.')
            return None
  

if __name__ == "__main__":
    img = JPG('bolt.jpg')
    print(img.img_data)