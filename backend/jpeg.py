#!/usr/bin/env python3

from struct import unpack
from typing import List
import os
import sys
import numpy as np

#Markers that are supported for JPEG/JFIF
supportedMarkers = {
    0xD8: 'Start of Image (SOI)',
    0xE0: 'JFIF segment marker (APP0)',
    0xE1: 'EXIF segment marker (APP1)',
    0xDB: 'Define Quantisation Table (DQT)',
    0xC0: 'Start of Frame (SOF)',
    0xC4: 'Define Huffman Table (DHT)',
    0xDA: 'Start of Scan (SOS)',
    0xD9: 'End of Image (EOI)',
    0xDD: 'Define Restart Interval (DRI)'
}

#Markers that are not supported for JPEG/JFIF
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
    0x01: 'TEM Marker - Arithmetic Coding',
    0xEF: 'APP15',
    0xDC: 'Define Number of Lines - DNL',
    0xDF: 'Expand Reference Component'
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
    
    #done
    def readHeader(self, data: List[int]) -> None:

        """
        Reads the byte in header and checks if byte is in supported/unsupported markers dictionary.
        If byte in unsupportedMarkers, raise error.
        If byte is supported, skip it.
        """

        #iterate through the data array and check if startOfScan attribute of the class has been set.
        #if SOS set, bitstreamIdx is set to current index i and exit loop.
        #finds the starting index of the bitstream in data array after SOS is found.
        currByte = 0
        for i in range(len(data)):
            if self.startOfScan.set:
                bitstreamIdx = i
                break

            currByte = data[i]
            if currByte != 0xFF: #0xFF byte is a marker segment identifier, all marker segments begin with FF
                continue

            currByte = data[i+1]
            if currByte == 0xFF or currByte == 0xD8 or currByte == 0xD9 or currByte == 0x01:
                i += 1
                continue
                
            markerLen = self.readMarkerLength(data, i+2)
            marker = supportedMarkers.get(currByte)

            if marker is None or marker in unsupportedMarkers:
                raise Exception(f"Error: Unsupported marker ({hex(currByte)}) found in file.")
            elif marker == 'Start of Frame (SOF)':
                self.readSOF(data, i, markerLen)
            elif marker == 'Start of Scan (SOS)':
                self.readSOS(data, i, markerLen)
            elif marker == 'Define Restart Interval (DRI)':
                self.readDRI(data, i, markerLen)
            elif marker == 'Define Huffman Table (DHT)':
                self.readHT(data, i, markerLen)
            elif marker == 'Define Quantisation Table (DQT)':
                self.readQT(data, i, markerLen)
            elif marker == 'JFIF segment marker (APP0)':
                self.readAPP0(data, i, markerLen)

        i += markerLen + 1

    #done
    def createHeaderByte(self, header: List[int]) -> None:

        """
        Adds markers to the header.
        If APP0 marker has any size, adds APP0 (JFIF segment marker) to header array
        Add StartOfFrame, HuffmanTables, QuantizationTable, StartOfScan
        """
        
        #Add StartOfImage - SOI (FFD8)
        header.append(0xFF)
        header.append(0xD8)

        if len(self.app0Marker) > 0:
            self.writeAPP0(header)

        self.writeSOF(header)
        self.writeHT(header, 0, 0)
        self.writeHT(header, 0, 1)
        self.writeHT(header, 1, 0)
        self.writeHT(header, 1, 1)
        self.writeQT(header)
        self.writeSOS(header)

    #done - revisit
    def readMarkerLength(self, data: List[int], start: int) -> int:
        markerLen = 0
        curr = start
        markerLen = markerLen | data[curr]
        curr += 1
        markerLen = markerLen << 8
        markerLen = markerLen | data[curr]
        return markerLen

    #done - revisit
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

    #done - revisit
    def writeSOS(self, data: List[int]) -> None:
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

    #done - revisit   
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

    #done - revisit
    def writeSOF(self, data: List[int]) -> None:
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

    #done - revisit
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

    #incomplete
    def writeHT(self, header: List[int], table: int, id: int) -> None:
        pass
    
    #revisit
    def readQT(self, data: List[int], start: int, length: int):
        self.quantizationTables.append(0xFF)
        self.quantizationTables.append(0xDB)

        for i in range(start, length):
            self.quantizationTables.append(data[i])

    #incomplete
    def writeQT(self, data: List[int]) -> None:
        pass

    #incomplete
    def readAPP0(self, data: List[int], start: int, length: int) -> None:
        pass

    #incomplete
    def writeAPP0(self, header: List[int]) -> None:
        pass
    
    #revisit
    def readDRI(self, data: List[int], start: int, length: int) -> None:
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

class MinimumCodedUnit:
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