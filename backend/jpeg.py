#!/usr/bin/env python3

from struct import unpack
from typing import List, Dict

#implement Reader class
from reader import BitReader
from writer import BitWriter
import os
import sys
import numpy as np


#Markers that are supported for JPEG/JFIF
supportedMarkers = {
    0xD8: 'Start of Image (SOI)',
    0xE0: 'JFIF segment marker (APP0)',
    0xE1: 'EXIF segment marker (APP1)',
    0xDB: 'Define Quantization Table (DQT)',
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

def loadJPEG(filename: str) -> List[int]:

    if not os.path.exists(filename):
        print(f'Error - {filename} file does not exist.')
        return None

    try:
        with open(filename, 'rb') as f:
            header = f.read(2)
            marker = (header[0] << 8) + header[1]
            unsigned_marker = (header[0] & 0xFF) * 256 + (header[1] & 0xFF)
            if marker != 0xFFD8 and marker not in supportedMarkers:
                print(unsigned_marker)
                raise ValueError(f'Error - {filename} file is not a valid JPEG file.')
            filedata = []
            while True:
                chunk_header = f.read(2)
                if not chunk_header:
                    break
                chunk_size = (chunk_header[0] << 8) + chunk_header[1]
                chunk_data = f.read(chunk_size-2)
                chunk = chunk_header + chunk_data
                filedata.extend(chunk)
            
            return filedata
                        
    except FileNotFoundError:
        print(f'Error - Cannot open {filename} file.')
        return None

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
        self.used = False

class QuantizationTable:
    def __init__(self, len: int, precision: int, dest_id: int) -> None:
        self.table: List[int] = [0] * 64
        self.length = len
        self.precision = precision
        self.dest_id = dest_id
        self.set: bool = False

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
        self.set: bool = False

class MinimumCodedUnit:
    def __init__(self) -> None:
        self.luminance = [Channel() for i in range (4)]
        self.chrominance = [Channel() for i in range(2)]   

class Header:
    def __init__(self) -> None:
        self.startOfFrame = StartOfFrame()
        self.startOfScan = StartOfScan()
        self.components: List[Component] = [Component() for i in range(3)] #list comprehension - creating new Component object on each iteration and appends to the list (Y'CbCr)
        self.dcHuffmanTables: List[HuffmanTable] = [HuffmanTable() for i in range(len(self.components))]
        self.acHuffmanTables: List[HuffmanTable] = [HuffmanTable() for i in range(len(self.components))]
        self.bitstreamIndex = 0
        self.restartInterval = 0
        self.quantizationTables: List[QuantizationTable] = []
        self.app0Marker = []
        self.zeroBased: bool = False
    
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
            elif marker == 'Define Quantization Table (DQT)':
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

    #done
    def readMarkerLength(self, data: List[int], start: int) -> int:

        """
        Retrieves the length of marker by combining two bytes into a single integer that represents the length of the marker.
        Does it by using bitwise OR operation twice (each for a byte).
        """

        markerLen = 0
        curr = start

        #store value of the first byte by using bitwise OR operation.
        markerLen = markerLen | data[curr]
        curr += 1

        #shift markerLen by 8 bits to the left to make room for the next byte
        #store value of next byte using bitwise OR operation
        #return markerLen
        markerLen = markerLen << 8
        markerLen = markerLen | data[curr]
        return markerLen

    #done
    def readSOS(self, data: List[int], start: int, len: int) -> None:

        """
        Reads the StartOfScan marker in the header. 
        """

        print('Reading Start of Scan ...')

        #skips 4 bytes, (marker and length)
        i = start + 4
        current = data[i]

        if current != self.startOfFrame.numOfComponents:
            raise Exception('Error - Wrong number of components in Start of Scan.')
        
        componentId = None
        for j in range(self.startOfFrame.numOfComponents):
            print(j)
            component = self.components[j]
            componentId = data[i+1]
            if componentId != component.identifier:
                raise Exception('Error - Wrong Component ID in Start of Scan.')
            component.acHuffmanTableId = data[i + 2] & 0x0F
            component.dcHuffmanTableId = data[i] >> 4
            i += 2
            
        i += 1
        if i != start + len - 1:
            raise Exception('Error - Number of bytes do not equal the length of marker.')
        self.startOfScan.set = True   
        print('Done.')     

    #done
    def writeSOS(self, header: List[int]) -> None:

        """
        Adds StartOfScan marker to the header.
        
        + FF DA
        + Length
        + Number of Components in Scan
        + For each component: componentID + HuffmanTable to use
        + 3 bytes to be ignored.

        Result of calculation is cast to 8 bits by using the bitwise AND operation with 0xFF
        """

        #add marker FFDA
        header.append(0xFF)
        header.append(0xDA)

        #add lenght - must be 6+2*(number of components in scan)
        header.append(0x00)
        header.append((6 + (2 * self.startOfFrame.numOfComponents)) & 0xFF)
        
        #add number of components in scan.
        header.append(self.startOfFrame.numOfComponents)

        #for each component add component id and huffmantable to use
        for i in range(self.startOfFrame.numOfComponents):
            header.append(self.components[i].identifier)
            j = (self.components[i].dcHuffmanTableId << 4) | self.components[i].acHuffmanTableId
            header.append(j & 0xff)
        
        #3 bytes to be ignored
        header.append(0x00)
        header.append(0x00)
        header.append(0x00)

    #done
    def readSOF(self, data: List[int], start: int, len: int) -> None:

        """
        Reads StartOfFrame marker in the header.

        + Length - 8+components*3
        + Data precision (0x08) - 8 bits precision: stored in startOfFrame.
        + Height and width of image: stored in startOfFrame.
        + Number of components - for each component reads its identifier, sampling factors and quantization table number: stores all in components.
        + Checks sampling factors of components are valid and raises an exception if not.
        + Checks length of data read matches the expected length and raises exception if the do not match.
        """

        print('Reading Start Of Frame (SOF0) ...')
        i = start + 4

        #checks if the data precision is exactly 8 bits and raises exception if not.
        #if precision is 8 bits, sets precision of startOfFrame object to data[i].
        if data[i] != 0x08:
            print(data[i])
            raise Exception('Invalid data precision.')
        self.startOfFrame.precision = data[i]
        
        #reading image height from data. 
        #height is 2 bytes therefore shift by 8 bits twice
        self.startOfFrame.height = self.startOfFrame.height + (data[i+1] << 8)
        i += 1
        self.startOfFrame.height = self.startOfFrame.height + data[i+1]
        i += 1
        
        #checks if image width is 0. Image heigth cannot be 0 px.
        if self.startOfFrame.height == 0:
            raise Exception('Error - Image height is 0 px.')

        #read image width from data
        #width is 2 bytes therefore shit by 8 bits twice
        self.startOfFrame.width = self.startOfFrame.width + (data[i+1] << 8)
        i += 1
        self.startOfFrame.width = self.startOfFrame.width + data[i+1]
        i += 1
        
        #checks if image width is 0. An image width cannot be 0 px
        if self.startOfFrame.width == 0:
            raise Exception('Error - Image width is 0 px.')

        #checks for making sure number of components are not 0, 4 or anything other than 1 and 3
        #colour component IDs can be 1,2,3 so if 0 zeroBased is set to True.  
        i += 1
        if data[i] == 0x00:
            raise Exception('Error - Number of colour components cannot be zero.')

        if data[i] == 0x04:
            raise Exception('Error - CMYK colour mode is not supported.')

        if data[i] != 0x01 and data[i] != 0x03:
            raise Exception('Error - Invalid number of components.')
        self.startOfFrame.numOfComponents = data[i]

        seen_ids = list()
        for j in range(self.startOfFrame.numOfComponents):
            comp = self.components[j]
            comp.identifier = data[i+1]

            if comp.identifier == 0:
                self.zeroBased = True
            if self.zeroBased:
                comp.identifier += 1

            i += 1
            comp.horizontalSamplingFactor = data[i+1] >> 4
            comp.verticalSamplingFactor = data[i+1] & 0x0F
            i += 1
            comp.quantizationTableNumber = data[i+1]
            i += 1

            if comp.identifier == 4 or comp.identifier == 5:
                raise Exception(f'Error - YIQ colour mode is not supported. ComponentID: {comp.identifier}')
            if comp.identifier == 0 or comp.identifier > 3:
                raise Exception(f'Error - Invalid colour component. ComponentID: {comp.identifier}')
            
            if comp.identifier in seen_ids:
                raise Exception(f'Error - Duplicate colour component ID: {comp.identifier}')
            seen_ids.append(comp.identifier)

        if self.startOfFrame.numOfComponents > 1:
            if ((self.components[0].verticalSamplingFactor != 1 and self.components[0].verticalSamplingFactor != 2)
            or (self.components[0].horizontalSamplingFactor != 1 and self.components[0].horizontalSamplingFactor != 2)
            or (self.components[1].horizontalSamplingFactor != 1 or self.components[1].verticalSamplingFactor != 1)
            or (self.components[2].horizontalSamplingFactor != 1 or self.components[2].verticalSamplingFactor != 1)):
                raise Exception('Error - Invalid sampling factor.')
        else:
            self.components[0].verticalSamplingFactor = 1
            self.components[0].horizontalSamplingFactor = 1
        
        
        if i != start + len + 1:
            print(i)
            raise Exception('Incorrect Start of Frame length.')
        self.startOfFrame.set = True

        #printing area
        print(f'Precision: {self.startOfFrame.precision}\nImage Size: {self.startOfFrame.width} x {self.startOfFrame.height}\nNumber of Image Components: {self.startOfFrame.numOfComponents}')
        for component in self.components:
            print(f'    Component ID: {component.identifier}, Quantisation Table ID: {component.quantizationTableNumber}')
        print('\nDone.\n-----------------------------------------------')

    #done
    def writeSOF(self, data: List[int]) -> None:
        
        """
        Adds StartOfFrame marker (SOF0)

        + Pushes SOF0 marker by appending (0xFF, and 0xC0) into the data array.
        + First byte of length of the marker segment (0x00).
        + Depending on the number of components in the image, pushes back the second byte of the length marker
            + (0x0B) for one componenet
            + (0x11) for more than one component.
        + Data precision (0x08)
        + Height and width in two bytes each. Split into high and low bytes by shifting the value of height/width right by 8 bits and masking the result with 0xFF
        + Number of components in the image
        + Iterate through the components for the number of components, and pushes the identifier, sampling factors and quantization table number of the component.
        """
        
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

    #done
    def readHT(self, data: List[int], start: int, len: int):

        """
        A single DHT segment may contain multiple Huffman Tables, each with its own information byte.
        FFC4: Marker (2)
        XXXX: Length (2)
        YY: Table information (1 byte): Lower (L) and Upper (U) nibble
            U: 0 | 1, 0: DC huffman table, 1: AC huffman table
            L: 0 - 3, table id. 
        [16]: Number of symbols with codes of that length 1-16 (16)
        [X]: Table containing the symbols in order of increasing code length. 
             (x = total number of codes)
        """
        
        print('Reading Define Huffman Table ...')
        
        hufftable = None
        i = start + 4
        tableInfo = data[i]
        tableType = (tableInfo >> 4)
        tableID = (tableInfo & 0x0F)
        
        while i < (start + len):
            
            #Checking upper nibble
            if (tableType) > 1:
                raise ValueError('Error - Wrong Huffman table class. Not AC or DC.')
            
            if (tableID) > 3:
                raise ValueError('Error- Wrong Huffman Table Destination Identifier')

            if (tableType) == 0:
                hufftable = self.dcHuffmanTables[tableID]
            else:
                hufftable = self.acHuffmanTables[tableID]

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
            getHuffmanCodes(hufftable)
            i += 1

            print(f'Huffman table length: {len}\nDestination ID: {tableID}\nClass: {tableType}\nTotal number of codes: {total}')
            print(hufftable.offsets)

        print('\nDone.\n-----------------------------------------------')
    #done - explain
    def writeHT(self, header: List[int], table: int, id: int) -> None:
        
        #Add Huffman Table marker bytes (FFC4)
        header.append(0xFF)
        header.append(0xC4)

        header.append(0x00)
        if table:
            header.append(0xB5)
        else:
            header.append(0x1F)

        i = table << 4
        i = i | (table & 0x0F)
        header.append(i)
        if table:
            huffTable = self.acHuffmanTables[id]
        else:
            huffTable = self.dcHuffmanTables[id]
        
        total = 0
        for j in range(16):
            codes = huffTable.offsets[i+1] - huffTable.offsets[i]
            total += codes
            header.append(codes & 0xFF)

        for j in range(codes):
            header.append(huffTable.symbols[i])
        pass
    
    #done
    def readQT(self, data: List[int], start: int, len: int):

        """
        Reads Quantization Tables from a given file data and append it to an array named quantizationTables
        """
        print('Reading Define Quantization Table (FFDB) ...')

        length = data[start + 3]
        tableID = data[start + 4] & 0x0F

        if tableID > 3:
            raise Exception(f'Error - Invalid quantization table ID: {tableID}')
        
        #precision = 16 bits
        if data[start + 4] >> 4 != 0:
            precision = 16
            qtable = QuantizationTable(length, precision, tableID)
            for i in range(start, start + len + 2):
                qtable.table[i - start - 5] = data[i]
            self.quantizationTables.append(qtable)
        #precision = 8 bits
        else:
            precision = 8
            qtable = QuantizationTable(length, precision, tableID)
            for i in range(start, start + len + 2):
                qtable.table[i - start - 5] = data[i]

            self.quantizationTables.append(qtable)

        for qt in self.quantizationTables:
            print(f'Table Length: {qt.length}\nPrecision: {qt.precision} bits\nDestination ID: {qt.dest_id}\n    {qt.table}\n')
        print('Done.\n-----------------------------------------------')

    #done
    def writeQT(self, header: List[int]) -> None:
        
        """
        Iterates over all elements in quantizationTables and appends each element to the header list. 
        """
        for i in self.quantizationTables:
            header.append(i)

    #incomplete - research and see are there other ways? Do we have to focus on APP0 only. APP1 is EXIF. 
    def readAPP0(self, data: List[int], start: int, len: int) -> None:
        pass

    #incomplete
    def writeAPP0(self, header: List[int]) -> None:
        pass
    
    #done - explain
    def readDRI(self, data: List[int], start: int, len: int) -> None:
        """
        Reads the Define Restart Interval Segment
        + FFDD : marker
        + 0004 : length - length must be 4
        + XXXX : restart interval
        Not all JPG files have restart intervals.
        """
        print('Reading Define Restart Interval ...')
        i  = start + 4
        if len != 4:
            raise ValueError('Error - Wrong length of Restart Interval Marker. Length is not 4.')
        self.restartInterval = self.restartInterval | data[i]
        self.restartInterval = self.restartInterval << 8
        self.restartInterval = self.restartInterval | data[i + 1]

        print(f'Restart Interval: {self.restartInterval}\nLength: {len}')
        print('\nDone.\n-----------------------------------------------')
        
class JPG:
    def __init__(self, file):
        self.header = Header()
        self.MCUVector: List[MinimumCodedUnit] = []
        self.currMCU = 0
        self.Channel = 0
        self.ChannelType = True
        self.Coefficient = 0
        self.Bits = 0
        data = loadJPEG(file)
        self.header.readHeader(data)
        self.readBitstream(data)
    
    #done - document
    def readBitstream(self, data: List[int]) -> None:

        s = []
        for i in range(self.header.bitstreamIndex, len(data)):
            s.append(data[i])
            if data[i] == 0xFF:
                if data[i+1] == 0x00:
                    i+=1
            
        bWidth = ((self.header.startOfFrame.width + 7) // 8)
        bHeight = ((self.header.startOfFrame.height + 7) // 8)

        if bWidth % 2 == 1 and self.header.components[0].horizontalSamplingFactor == 2:
            bWidth += 1
        
        if bHeight % 2 == 1 and self.header.components[0].verticalSamplingFactor == 2:
            bHeight += 1

        blocks = bHeight * bWidth
        noOfMCU = blocks // (self.header.components[0].verticalSamplingFactor * self.header.components[0].horizontalSamplingFactor)
        finalDcCoeff = 0

        bits = BitReader(s)

        for i in range(noOfMCU):
            mcu = MinimumCodedUnit()
            if len(self.MCUVector) == 0:
                finalDcCoeff = 0
            else:
                finalDcCoeff = self.MCUVector[-1].chrominance[1].dcCoeff

            self.readNextMCU(mcu, bits, finalDcCoeff)
            self.MCUVector.append(mcu)

    #done - document, finalDcCoeff not used?
    def readBlock(self, channel: Channel, bit: BitReader, finalDcCoeff: int, dc: HuffmanTable, ac: HuffmanTable) -> None:

        symbol = self.readNextSymbol(bit, dc)
        coeffLen: int = 0
        coeffSigned: int = 0
        coeffUnsigned: int = 0

        if symbol == 0x00:
            channel.dcCoeff = 0
        else:
            coeffLen = symbol & 0x0F
            coeffUnsigned = bit.readNextBits(coeffLen)
            if coeffUnsigned < pow(2, coeffLen - 1):
                coeffSigned = coeffUnsigned - pow(2, coeffLen) + 1
            else:
                coeffSigned = int(coeffUnsigned)
            channel.dcCoeff = coeffSigned
        
        coeffRead: int = 0
        while coeffRead < 63:
            symbol = self.readNextSymbol(bit, ac)
            if symbol == 0x00:
                break
            elif symbol == 0xF0:
                coeffRead += 16
                continue
            else:
                coeffLen = symbol & 0x0F
                zeros = int((symbol >> 4) & 0x0F)
                coeffRead += zeros
                coeffUnsigned = bit.readNextBits(coeffLen)
                if coeffUnsigned < pow(2, coeffLen - 1):
                    coeffSigned = coeffUnsigned - pow(2, coeffLen) + 1

                else:
                    coeffSigned = int(coeffUnsigned)
                channel.acCoeff[coeffRead] = coeffSigned
                coeffRead += 1

                if coeffSigned != 0 and coeffSigned != 1:
                    self.Bits += 1 

    def BlockToBitstream(self) -> None:
        pass

    def extractFromJPG(self, secretMedium: List[int]) -> None:
        pass

    def newBitstream(self, stream: List[int]) -> None:
        pass

    def MCUtoBitstream(self) -> None:
        pass

    def resetCurr(self) -> None:
        pass

    def readNextSymbol(self, bits: BitReader, huffmanTable: HuffmanTable) -> int:
        code: int = 0
        codeIdx: int = 0
        codeFound: bool = False
        codeLen: int = 1

        while(codeLen <= 16 and not codeFound):
            code = code << 1
            code = code | (bits.readNextBits() & 0x01)
            start = huffmanTable.offsets[codeLen -1]
            mask = (1 << codeLen) - 1
            for i in range(start, huffmanTable.offsets[codeLen]):
                if(code & mask) == (huffmanTable.codes[i] & mask):                    
                    codeFound = True
                    codeIdx = i
                    break
            if not codeFound:
                codeLen += 1
        
        return huffmanTable.symbols[codeIdx]

    def getNextFreeCoeff(self) -> int:
        i = self.getNextCoeff()
        while i[0] == 0 or i[0] == 1:
            i = self.getNextFreeCoeff()
        return i

    def getNextCoeff(self) -> int:
        pass

        #needs work
        #self.img_data = self.readJPG(file)

    def readNextMCU(self, mcu: MinimumCodedUnit, bit: BitReader, finalDcCoeff: int) -> None:
        #could add number of components check.
        luminanceBlocks = self.header.components[0].horizontalSamplingFactor * self.header.components[0].verticalSamplingFactor

        for i in range(luminanceBlocks):
            self.readBlock(mcu.luminance[i], bit, finalDcCoeff, self.header.dcHuffmanTables[self.header.components[0].dcHuffmanTableId], self.header.acHuffmanTables[self.header.components[0].acHuffmanTableId])
            finalDcCoeff = mcu.luminance[i].dcCoeff

        if self.header.startOfFrame.numOfComponents > 1:
            self.readBlock(mcu.chrominance[0], bit, finalDcCoeff, self.header.dcHuffmanTables[self.header.components[1].dcHuffmanTableId], self.header.acHuffmanTables[self.header.components[1].acHuffmanTableId])
            finalDcCoeff = mcu.chrominance[0].dcCoeff

            # print(self.header.dcHuffmanTables[self.header.components[2].dcHuffmanTableId])
            # print(self.header.acHuffmanTables[self.header.components[2].acHuffmanTableId])

            self.readBlock(mcu.chrominance[1], bit, finalDcCoeff, self.header.dcHuffmanTables[self.header.components[2].dcHuffmanTableId], self.header.acHuffmanTables[self.header.components[2].acHuffmanTableId])

def getHuffmanCodes(huffmanTable: HuffmanTable) -> None:
    code = 0
    for offset in range(16):
        for i in range(huffmanTable.offsets[offset], huffmanTable.offsets[offset + 1]):
            huffmanTable.codes[i] = code
            code += 1
        code = code << 1

if __name__ == "__main__":
    img = JPG('bird.jpg')
    