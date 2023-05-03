from typing import List
from reader import BitReader
from writer import BitWriter
import os
import json
import logging
import numpy as np

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('vault-logger')

# Markers that are supported for JPEG/JFIF
# These markers are set by Joint Photographics Expert Group, they do not differ, so if it highlights for plaigarism ignore. You can refer to the JPEG standard specification.
supportedMarkers = {
    0xD8: 'Start of Image (SOI)',
    0xE0: 'JFIF segment marker (APP0)',
    0xDB: 'Define Quantization Table (DQT)',
    0xC0: 'Start of Frame (SOF)',
    0xC4: 'Define Huffman Table (DHT)',
    0xDA: 'Start of Scan (SOS)',
    0xD9: 'End of Image (EOI)',
    0xDD: 'Define Restart Interval (DRI)'
}

# Markers that are not supported for JPEG/JFIF
# These markers are set by Joint Photographics Expert Group, they do not differ, so if it highlights for plaigarism ignore. You can refer to the JPEG standard specification.
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

# opens the image file and reads it in chunks. 
def loadJPEG(filename: str) -> bytearray:
    try:
        with open(filename, 'rb+') as f: # read and write binary mode.
            header = f.read(2)
            if len(header) < 2:
                raise RuntimeError(f' {os.path.basename(filename)} is empty.')
            else:
                # combines the first 2 bytes to get 16-bit integer value the first marker segment in file. If FFD8, file is a jpeg image. 
                marker = (header[0] << 8) + header[1]
                if marker != 0xFFD8:
                    raise RuntimeError(f' {os.path.basename(filename)} file is not a valid JPEG file.')
                
                filedata = [header[0], header[1]]
                
                # read file in chunks, loop continues until no more data to read from file.
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
        logger.error(f'Error - Cannot open {filename} file.')
        return None

    except RuntimeError as e:
        logger.error(str(e))
        return None

class CodeWrapper:
    def __init__(self, code: int = 0, length: int = 0) -> None:
        self.code: int = code
        self.length: int = length

class StartOfFrame:
    def __init__(self) -> None:
        self.precision = 0
        self.height = 0
        self.width = 0
        self.numOfComponents = 0x00
        self.set = False

#Component Class (Y'CbCr)
class Component:
    def __init__(self) -> None:
        self.identifier: int = 0
        self.quantizationTableNumber: int = 0
        self.acHuffmanTableId: int = 0
        self.dcHuffmanTableId: int = 0
        self.verticalSamplingFactor: int = 0
        self.horizontalSamplingFactor: int = 0
        self.used: bool = False

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
        self.acCoeff = [0] * 63     #AC coefficients of pixel block 63 because there are 63 AC coefficients and 1 DC coefficient = 64 (8x8 block)

    def __str__(self) -> str:
        print(self.acCoeff)

#Huffman Table Class (Multiple Tables in single JPEG)
class HuffmanTable:
    def __init__(self) -> None:
        self.symbols = [0x00]*162
        self.offsets = [0]*17
        self.codes = [0]*162
        self.set = False
        self.table_length = 0
        self.destination_id = 0
        self.table_type = 0
        self.numberOfCodes = 0

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
        self.dcHuffmanTables: List[HuffmanTable] = [HuffmanTable() for i in range(2)]
        self.acHuffmanTables: List[HuffmanTable] = [HuffmanTable() for i in range(2)]
        self.bitstreamIndex = 0
        self.restartInterval = 0
        self.quantizationTables: List[QuantizationTable] = []
        self.quantizationTablesData: List[int] = []
        self.app0Marker: bytearray = []
        self.zeroBased: bool = False # if False, colour IDs (1,2,3) - if True, colour ID is 0.
        self.startOfSelection: int = 0
        self.endOfSeleciton: int = 0
        self.successiveApproxHigh: int = 0
        self.successiveApproxLow: int = 0

    def __str__(self) -> str:

        #START OF FRAME
        startOfFramePrecision = self.startOfFrame.precision
        startOfFrameImageSize = f'{self.startOfFrame.width} x {self.startOfFrame.height}'
        startOfFrameNumberOfComponents = self.startOfFrame.numOfComponents
        startOfFrameComponents = list()
        for sof_component in self.components:
            if sof_component.identifier == 1:
                channel = 'Luminance (Y)'
            elif sof_component.identifier == 2:
                channel = 'Chroma blue (Cb)'
            elif sof_component.identifier == 3:
                channel = 'Chroma red (Cr)'
            component_dict = {'Component ID': sof_component.identifier, 'Channel': channel ,'Quantization Table ID': sof_component.quantizationTableNumber}
            startOfFrameComponents.append(component_dict)

        #DEFINE QUANTIZATION TABLE
        defineQuantizationTables = list()
        for quantization_table in self.quantizationTables:
            qt_dict = {
                'Table Length': quantization_table.length,
                'Precision': f'{quantization_table.precision} bits',
                'Destination ID': quantization_table.dest_id,
                'Quantization Values': f'{quantization_table.table}'
            }
            defineQuantizationTables.append(qt_dict)

        #DEFINE HUFFMAN TABLE
        defineHuffmanTables = list()

        for ac_huffman_table in self.acHuffmanTables:
            if ac_huffman_table.table_type == 1: table_type = 'AC table' 
            else: table_type = 'DC table'
            ac_huffman_symbols = dict()
            for i in range(16):
                ac_huffman_symbols[f'{i+1} bits'] = list()
                for j in range(ac_huffman_table.offsets[i], ac_huffman_table.offsets[i+1]):
                    ac_huffman_symbols[f'{i+1} bits'].append(format(ac_huffman_table.symbols[j], "02X"))


            ac_dict = {
                'Huffman Table Length': ac_huffman_table.table_length,
                'Destination ID' : ac_huffman_table.destination_id,
                'Class' : f'{ac_huffman_table.table_type} ({table_type})',
                'Total number of codes': ac_huffman_table.numberOfCodes,
                'Offsets' : f'{ac_huffman_table.offsets}',
                'Huffman Codes' : f'{ac_huffman_symbols}'   
            }
            defineHuffmanTables.append(ac_dict)

        for dc_huffman_table in self.dcHuffmanTables:
            if dc_huffman_table.table_type == 1: table_type = 'AC table'
            else: table_type = 'DC table'
            dc_huffman_symbols = dict()
            for x in range(16):
                dc_huffman_symbols[f'{x+1} bits'] = list()
                for y in range(dc_huffman_table.offsets[x], dc_huffman_table.offsets[x+1]):
                    dc_huffman_symbols[f'{x+1} bits'].append(format(dc_huffman_table.symbols[y], "02X"))
            
            dc_dict = {
                'Huffman Table Length': dc_huffman_table.table_length,
                'Destination ID': dc_huffman_table.destination_id,
                'Class': f'{dc_huffman_table.table_type} ({table_type})',
                'Total number of codes': dc_huffman_table.numberOfCodes,
                'Offsets': f'{dc_huffman_table.offsets}',
                'Huffman Codes': f'{dc_huffman_symbols}' 
            }
            defineHuffmanTables.append(dc_dict)

        #START OF SCAN
        startOfScanStartOfSelection = self.startOfSelection
        startOfScanEndOfSelection = self.endOfSeleciton
        startOfScanSuccessiveApproximation = f'0x{self.successiveApproxHigh, self.successiveApproxLow}'
        startOfScanImageComponents = list()
        for i in range(self.startOfFrame.numOfComponents):
            sos_component = self.components[i]
            sos_dict = {
                'Component ID' : sos_component.identifier,
                'AC Huffman Table ID': sos_component.acHuffmanTableId,
                'DC Huffman Table ID': sos_component.dcHuffmanTableId
            }
            startOfScanImageComponents.append(sos_dict)            

        output = {
            'Start Of Frame (SOF)': { 
                'Data Precision': startOfFramePrecision,
                'Image Size': startOfFrameImageSize,
                'Number of Colour Components': startOfFrameNumberOfComponents,
                'Colour Components': startOfFrameComponents
            },
            'Start Of Scan (SOS)': {
                'Components': startOfScanImageComponents,
                'Spectral selection' : f'{startOfScanStartOfSelection}...{startOfScanEndOfSelection}',
                'Successive approximation': f'0x{startOfScanSuccessiveApproximation}'
            },
            'Define Quantization Tables' : defineQuantizationTables,
            'Define Huffman Tables' : defineHuffmanTables
        }
       
        return json.dumps(output, indent=4)

    def readHeader(self, data: bytearray) -> None:
        """
        Reads the byte in header and checks if byte is in supported/unsupported markers dictionary.
        If byte in unsupportedMarkers, raise error.
        If byte is supported, skip it.
        """
        #iterate through the data array and check if startOfScan attribute of the class has been set.
        #if SOS set, bitstreamIdx is set to current index i and exit loop.
        #finds the starting index of the bitstream in data array after SOS is found.
        currByte = 0
        i = 0
        while i < len(data):
            if self.startOfScan.set:
                self.bitstreamIndex = i
                break

            currByte = data[i]
            if currByte != 0xFF: #0xFF byte is a marker segment identifier, all marker segments begin with FF
                i += 1
                continue
            
            i += 1
            currByte = data[i]
          
            if currByte in [0xD8, 0xD9, 0x01, 0xFF]:
                i += 1
                continue
            
            i += 1    
            markerLen = self.readMarkerLength(data, i)
            marker = supportedMarkers.get(currByte)
            if marker == 'Start of Frame (SOF)':
                self.readSOF(data, i, markerLen)
            elif marker == 'Start of Scan (SOS)':
                self.readSOS(data, i, markerLen)
            elif marker == 'Define Restart Interval (DRI)':
                self.readDRI(data, i, markerLen)
            elif marker == 'Define Huffman Table (DHT)':
                self.readDHT(data, i, markerLen)
            elif marker == 'Define Quantization Table (DQT)':
                self.readDQT(data, i, markerLen)
            elif marker == 'JFIF segment marker (APP0)':
                self.readAPP0(data, i, markerLen)
            elif marker in unsupportedMarkers:
                raise Exception(f"Error: Unsupported marker ({hex(currByte)}) found in file.")

            i += markerLen
            
    def createHeaderByte(self, header: bytearray) -> None:

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
        self.writeDHT(header, 0, 0)
        self.writeDHT(header, 0, 1)
        self.writeDHT(header, 1, 0)
        self.writeDHT(header, 1, 1)
        self.writeDQT(header)
        self.writeSOS(header)

    def readMarkerLength(self, data: bytearray, start: int) -> int:

        """
        Retrieves the length of marker by combining two bytes into a single integer that represents the length of the marker.
        Does it by using bitwise OR operation twice (each for a byte).
        """

        length = 0
        curr = start

        length = length | data[curr]
        curr += 1

        length = length << 8
        length = length | data[curr]
        return length

    def readSOS(self, data: bytearray, start: int, len: int) -> None:

        logger.info(' Reading Start of Scan (SOS)')
        i = start + 2
        currentByte = data[i]

        if currentByte != self.startOfFrame.numOfComponents:
            raise Exception('Error - Wrong number of components in Start of Scan.')
        
        componentId = None
        for j in range(self.startOfFrame.numOfComponents):
            component = self.components[j]
            i += 1
            componentId = data[i]
            if componentId != component.identifier:
                raise Exception('Error - Wrong Component ID in Start of Scan.')
            
            i += 1
            acId = data[i] & 0x0F
            if acId > 3:
                raise Exception(f'Error - Invalid Huffman AC table ID: {acId}')
            else:
                component.acHuffmanTableId = acId

            dcId = data[i] >> 4
            if dcId > 3:
                raise Exception(f'Error - Invalid Huffman DC table ID: {dcId}')
            else:
                component.dcHuffmanTableId = dcId

        # the following are for progressive JPEGs, they are not that important, however a positive to include. 
        i += 1
        startOfSelection = data[i]
        i += 1
        endOfSelection = data[i]
        i += 1
        successiveApprox = data[i]

        self.startOfSelection = startOfSelection
        self.endOfSeleciton = endOfSelection
        self.successiveApproxHigh = successiveApprox >> 4
        self.successiveApproxLow = successiveApprox & 0x0F

        if (self.startOfSelection != 0 or self.endOfSeleciton != 63):
            raise Exception('Error - Invalid spectral selection')

        if (self.successiveApproxHigh != 0 or self.successiveApproxLow != 0):
            raise Exception('Error - Invalid successive approximation') 

        if i != start + len - 1:
            raise Exception('Error - Number of bytes do not equal the length of marker.')
        self.startOfScan.set = True          
    
    def writeSOS(self, header: bytearray) -> None:
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
        #add length - must be 6+2*(number of components in scan)
        header.append(0x00)
        header.append(6 + (2 * self.startOfFrame.numOfComponents))
        #add number of components in scan.
        header.append(self.startOfFrame.numOfComponents)

        #for each component add component id and huffmantable to use
        for i in range(self.startOfFrame.numOfComponents):
            header.append(self.components[i].identifier)
            j = self.components[i].dcHuffmanTableId
            j = j << 4
            j = j | self.components[i].acHuffmanTableId
            header.append(j)
        #3 bytes to be ignored
        header.append(0x00)
        header.append(0x3F)
        header.append(0x00)

    def readSOF(self, data: bytearray, start: int, len: int) -> None:
        """
        Reads StartOfFrame marker in the header.
        + Length - 8+components*3
        + Data precision (0x08) - 8 bits precision: stored in startOfFrame.
        + Height and width of image: stored in startOfFrame.
        + Number of components - for each component reads its identifier, sampling factors and quantization table number: stores all in components.
        + Checks sampling factors of components are valid and raises an exception if not.
        + Checks length of data read matches the expected length and raises exception if the do not match.
        """
        logger.info(' Reading Start Of Frame (SOF0)')
        i = start + 2

        #checks if the data precision is exactly 8 bits and raises exception if not.
        #if precision is 8 bits, sets precision of startOfFrame object to data[i].
        if data[i] != 0x08:
            raise Exception('Invalid data precision.')
        self.startOfFrame.precision = data[i]
        
        #reading image height from data. 
        #height is 2 bytes therefore shift by 8 bits twice
        i += 1
        self.startOfFrame.height = self.startOfFrame.height + (data[i] << 8)
        i += 1    
        self.startOfFrame.height = self.startOfFrame.height + data[i]
        
        #checks if image height is 0. Image height cannot be 0 px.
        if self.startOfFrame.height == 0:
            raise Exception('Error - Image height is 0 px.')

        #read image width from data
        #width is 2 bytes therefore shit by 8 bits twice
        i += 1
        self.startOfFrame.width = self.startOfFrame.width + (data[i] << 8)
        i += 1
        self.startOfFrame.width = self.startOfFrame.width + data[i]
        
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
            
            i += 1
            comp.identifier = data[i]

            #if colour component ID is 0, sets the zeroBased flag in Header to True.
            if comp.identifier == 0:
                self.zeroBased = True
            #this ensures that all components IDs are adjusted to 1,2,3 from 0,1,2
            if self.zeroBased:
                comp.identifier += 1

            i += 1
            comp.horizontalSamplingFactor = data[i] >> 4
            comp.verticalSamplingFactor = data[i] & 0x0F
            i += 1
            comp.quantizationTableNumber = data[i]
            
            #to check component identifiers are supported. If component ID is not 1 or 2 or 3, image is other than YCbCr.
            if comp.identifier == 4 or comp.identifier == 5:
                raise Exception(f'Error - YIQ colour mode is not supported. ComponentID: {comp.identifier}')
            if comp.identifier == 0 or comp.identifier > 3:
                raise Exception(f'Error - Invalid colour component. ComponentID: {comp.identifier}')
            if comp.identifier in seen_ids:
                raise Exception(f'Error - Duplicate colour component ID: {comp.identifier}')
            seen_ids.append(comp.identifier)

        #checks if horizontal and vertical sampling factors of colour components are supported by JPEG. 
        if self.startOfFrame.numOfComponents > 1:
            if ((self.components[0].verticalSamplingFactor != 1 and self.components[0].verticalSamplingFactor != 2)
            or (self.components[0].horizontalSamplingFactor != 1 and self.components[0].horizontalSamplingFactor != 2)
            or (self.components[1].horizontalSamplingFactor != 1 or self.components[1].verticalSamplingFactor != 1)
            or (self.components[2].horizontalSamplingFactor != 1 or self.components[2].verticalSamplingFactor != 1)):
                raise Exception('Error - Invalid sampling factor.')
        else:
            self.components[0].verticalSamplingFactor = 1
            self.components[0].horizontalSamplingFactor = 1
           
        if i != start + len - 1:
            raise Exception('Incorrect Start of Frame length.')
        self.startOfFrame.set = True

    def writeSOF(self, data: bytearray) -> None:
        
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
            data.append(self.components[i].identifier & 0xFF)
            c = (self.components[i].horizontalSamplingFactor & 0x0F) << 4
            c = c | (self.components[i].verticalSamplingFactor & 0x0F)
            data.append(c)
            data.append(self.components[i].quantizationTableNumber & 0xFF)

    def readDHT(self, data: bytearray, start: int, len: int):
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
        logger.info(' Reading Define Huffman Table (DHT)')
        
        hufftable = None
        i = start + 2

        tableType = data[i] >> 4
        tableId = data[i] & 0x0F
        while i < (start + len):
            
            #Checking upper nibble
            if tableType > 1 or tableType < 0:
                raise ValueError('Error - Wrong Huffman table class. Not AC or DC.')
            
            if tableId > 3 or tableId < 0:
                raise ValueError('Error- Wrong Huffman Table Destination Identifier')

            if tableType == 0:
                hufftable = self.dcHuffmanTables[tableId]
                hufftable.table_type = 0
            elif tableType == 1:
                hufftable = self.acHuffmanTables[tableId]
                hufftable.table_type = 1
            else:
                raise ValueError(f'Error - Wrong huffman table ID: {tableType}')

            if hufftable.set:
                raise ValueError('Error - Huffman table was assigned multiple times.')

            allCodes = 0
            # reading 16 bytes which represent codes of each length from 1 - 16 bits long.
            for j in range(1,17):
                i += 1
                # keeps total symbols by reading the next byte
                allCodes += data[i]
                # use the current value of total symbols to set the next value in offsets array.
                hufftable.offsets[j] = allCodes

            # reading next chunk of bytes which are all the symbols and store them in a straight line in the symbols array.
            for j in range(allCodes):
                i += 1
                hufftable.symbols[j] = data[i]

            hufftable.numberOfCodes = allCodes
            hufftable.table_length = len
            hufftable.destination_id = tableId
            hufftable.set = True
            generateHuffmanCodes(hufftable)
            i += 1

    def writeDHT(self, data: bytearray, table: int, id: int) -> None:
        
        #Add Huffman Table marker bytes (FFC4)
        data.append(0xFF)
        data.append(0xC4)
        data.append(0x00)
        
        if table:
            data.append(0xB5)
        else:
            data.append(0x1F)

        i = table
        i = i << 4
        i = i | (id & 0x0F)
        data.append(i)
        
        huffTable = None
        if table:
            huffTable = self.acHuffmanTables[id]
        else:
            huffTable = self.dcHuffmanTables[id]
        
        total_codes = 0
        number_of_codes = 0
        for j in range(16):
            number_of_codes = huffTable.offsets[j+1] - huffTable.offsets[j]
            total_codes += number_of_codes
            data.append(number_of_codes & 0xFF)

        for j in range(total_codes):
            data.append(huffTable.symbols[j])
    
    def readDQT(self, data: bytearray, start: int, length: int):
        """
        Reads Quantization Tables from a given file data and append it to an array named quantizationTables
        """
        logger.info(' Reading Define Quantization Table (FFDB)')

        length = data[start + 1]
        table_info = data[start + 2]
        table_precision = table_info >> 4
        table_id = table_info & 0x0F

        if table_id > 3:
            raise Exception(f'Error - Invalid quantization table ID: {table_id}')
        
        if table_precision != 0:
            quantization_table = QuantizationTable(length, 16, table_id)
            for i in range(start + 1, start + length):
                quantization_table.table[i - start - 3] = data[i]
            self.quantizationTables.append(quantization_table)
        else:
            quantization_table = QuantizationTable(length, 8, table_id)
            for i in range(start + 1, start + length):
                quantization_table.table[i - start - 3] = data[i]
            self.quantizationTables.append(quantization_table)
        
        self.quantizationTablesData.append(0xFF)
        self.quantizationTablesData.append(0xDB)
        for i in range(start, start + length):
            self.quantizationTablesData.append(data[i])

    def writeDQT(self, header: bytearray) -> None:
        
        """
        Iterates over all elements in quantizationTables and appends each element to the header list. 
        """
        for i in self.quantizationTablesData:
            header.append(i)

    def readAPP0(self, data: bytearray, start: int, len: int) -> None:
        """
        Reads APP0 (JFIF) marker segment
        """
        logger.info(' Reading JFIF Segment Marker (APP0)')
        self.app0Marker = data[start : start + len]

    def writeAPP0(self, header: bytearray) -> None:   
        header.append(0xFF)
        header.append(0xE0)
        for i in self.app0Marker:
            header.append(i)
        
    def readDRI(self, data: bytearray, start: int, len: int) -> None:
        """
        Reads the Define Restart Interval Segment
        + FFDD : marker
        + 0004 : length - length must be 4
        + XXXX : restart interval
        Not all JPG files have restart intervals.
        """
        logger.info('Reading Define Restart Interval (DRI)')
        i  = start + 2
        if len != 4:
            raise ValueError('Error - Wrong length of Restart Interval Marker. Length is not 4.')
        self.restartInterval = self.restartInterval | data[i]
        self.restartInterval = self.restartInterval << 8

        i += 1
        self.restartInterval = self.restartInterval | data[i]

    def generateSymbolCode(self, symbol: int, isAC: bool, isChrominance: bool, wrapper: CodeWrapper) -> None:
        """
        used during encoding, converts the symbols to a code before it is written to the bitstream.
        function takes a symbol, and two boolean parameters to indicate if the symbol is AC/DC symbol, chrominance/luminance symbol.
        takes a code wrapper object that holds the code itself, and the length in bits.
        """
        # checks if the symbol is used to represent the AC coefficient or DC coefficient.
        if isAC:
            huffman_table = self.acHuffmanTables[isChrominance]
        else:
            huffman_table = self.dcHuffmanTables[isChrominance]

        # using similar technique to generateHuffmanCodes(), we access the offset array to get the starting index of coefficients of each length inside the symbols array of HuffmanTable.
        for offset in range(16):
            # offset stores the first index at which symbols of specific bit length start in the symbols array
            # for however many codes of a specific length in the symbols array we compare the symbols until a match is found.
            for idx in range(huffman_table.offsets[offset], huffman_table.offsets[offset + 1]):
                if huffman_table.symbols[idx] == symbol:
                    wrapper.code = huffman_table.codes[idx] # after match found, code is set to corresponding code in the codes array of HuffmanTable
                    wrapper.length = offset + 1 # offset array starts with an extra 0, which is to represent there are 0 symbols of 1 bit length, to avoid falling behind we add + 1
                    return
        
        # if code is not found, raise error. 02X formatting allows us to see the symbol in hex.
        message = f"Code for {symbol:02X} cannot be found in Huffman table."
        raise RuntimeError(message)

    def fillHeaderBytes(self, header: bytearray) -> None:
        # add StartOfImage marker (FFD8)
        header.append(0xFF) 
        header.append(0xD8)

        # write JFIF APP0 segment marker
        if len(self.app0Marker) > 0:
            self.writeAPP0(header)

        # write Define Quantization Table marker
        self.writeDQT(header)

        # write StartOfFrame markers
        self.writeSOF(header)

        # write Define Huffman Table markers
        self.writeDHT(header, 0, 0)
        self.writeDHT(header, 0, 1)
        self.writeDHT(header, 1, 0)
        self.writeDHT(header, 1, 1)

        # write StartOfScan marker
        self.writeSOS(header)

class JPG:
    def __init__(self, file):
        self.header = Header()
        self.MCUVector: List[MinimumCodedUnit] = []
        self.currMCU = 0
        self.ChannelNumber = 0
        self.ChannelType = True
        self.Coefficient = 0
        self.Bits = 0
        data = loadJPEG(file)
        self.header.readHeader(data)
        self.decodeBitstream(data)

    def __str__(self) -> str:
        return str(self.header)
    
    def decodeBitstream(self, data: bytearray) -> None:
        """
        Reads the bitstream of JPG image.
        """

        # initialises a bytestream array.
        # current byte at index i is appended to bytestream
        # if current byte and current byte + 1 are FF00, increments index.
        # FF is used to indicate new marker segment, FF00 is byte stuffing to stop encoder from assuming it is new segment.
        bytestream = []
        i = self.header.bitstreamIndex        
        while i < len(data):
            bytestream.append(data[i])
            if data[i] == 0xFF:
                if data[i+1] == 0x00:
                    i+=1
            i+=1
        
        # adds 7 to the width & height and divides by 8 to round up width & height to the nearest multiple of 8 pixels.
        # done because JPEG compression works on 8x8 Minimum Coded Units (MCU).
        bWidth = (self.header.startOfFrame.width + 7) // 8
        bHeight = (self.header.startOfFrame.height + 7) // 8

        # checks if block width & height are odd
        # checks if luminance component horizontal and vertical sampling factors are 2
        # if odd and 2, last column or row of blocks will not be complete. 
        if bWidth % 2 == 1 and self.header.components[0].horizontalSamplingFactor == 2:
            # adds extra block to width to ensure last row of blocks is complete
            bWidth += 1
        
        if bHeight % 2 == 1 and self.header.components[0].verticalSamplingFactor == 2:
            # adds extra block to height to ensure last row of blocks is complete
            bHeight += 1

        totalBlocks = bHeight * bWidth
        totalMCU = totalBlocks // (self.header.components[0].verticalSamplingFactor * self.header.components[0].horizontalSamplingFactor)
        # print(totalMCU)

        # decodes each MCU by iterating totalMCU times.
        # appends each decoded MCU to MCUVector
        # The DC coefficient of each MCU is relative to the previous one, therefore a track of it is kept with finalDcCoeff.
        finalDcCoeff: int = 0
        bits = BitReader(bytestream)
        for i in range(totalMCU):
            mcu = MinimumCodedUnit()
            if len(self.MCUVector) == 0:
                finalDcCoeff = 0
            else:
                finalDcCoeff = self.MCUVector[-1].chrominance[1].dcCoeff
            self.decodeMCU(mcu, bits, finalDcCoeff)
            self.MCUVector.append(mcu)

    def decodeBlock(self, channel: Channel, bit: BitReader, finalDcCoeff: int, dc: HuffmanTable, ac: HuffmanTable) -> None:

        """USED TO HUFFMAN DECODE THE BITSTREAM"""

        symbol = self.readNextSymbol(bit, dc)

        # [START] for DC coefficients in the 8x8 block.
        if symbol == 0x00:
            channel.dcCoeff = 0
        else:
            # lower 4 bits of the symbol byte is the coefficient length. & 0x0F is used for getting the lower 4 bits of a byte.
            coefficient_length = symbol & 0x0F 
            coefficient_unsigned = bit.readNextBit(coefficient_length)
            # this is the bit that checks if the full bit length is used to represent a positive coefficient or negative coefficient. 
            # referring to the dissertation, the coefficients that have 0 in their top most significant bit can be repurposed to represent negative coefficients of same length of bits.
            # repurpose a coefficient if unsigned coefficient is less than the mirroring point which is 2^length-1, converted to the negative by 2^(length)+1
            # signed coefficients can be thought as the negative and positive "signed" coefficients. eg: -2,-1,1,2....
            # unsigned coefficients can be thought as the positive "non-signed" coefficients. eg: 1,2,3,4,5....
            if coefficient_unsigned < pow(2, coefficient_length - 1):
                coefficient_signed = coefficient_unsigned - pow(2, coefficient_length) + 1
            else:
                coefficient_signed = coefficient_unsigned
            channel.dcCoeff = coefficient_signed
            # [END] for DC coefficients.
        
        # [START] for AC coefficients in the 8x8 block
        # maximum 63 AC coefficients can be read for an 8x8 block, starting coefficient is the DC coefficient - processed separately.
        coefficient_read: int = 0
        while coefficient_read < 63:
            symbol = self.readNextSymbol(bit, ac)
            # refer to dissertation - 0x00 is a special symbol to indicate the END OF BLOCK - meaning rest of the coefficients in the 8x8 block are all 0s. 
            # there are no non-zero coefficients in the block from this point onwards so escape the function.
            if symbol == 0x00:
                break
            # refer to dissertation - 0xF0 is a special symbol to indicate the run length (number of 0s preceding the coefficient) is 16. Only 16 zeros can be processed at a time.
            # if 0xF0 is encountered, increment coefficient read by 16, because there are 16 zero coefficients between the two non-zero coefficients.
            elif symbol == 0xF0:
                coefficient_read += 16
                continue
            # If symbol is not special symbols, find coefficient length by getting the lower 4 bits of the byte - & 0x0F
            # the run length (zeros preceding the coefficient) is the upper 4 bits of a byte - >> 4
            else:
                coefficient_length = symbol & 0x0F
                runlength = (symbol >> 4) & 0x0F
                # increment the coefficients read by the amount of zeros in the symbol. 
                coefficient_read += runlength
                # read coefficient_length amount of bits to get the actual coefficient value
                coefficient_unsigned = bit.readNextBit(coefficient_length)
                # check if coefficient is repurposed to represent a negative coefficient, if so convert it to signed by applying 2^(length)+1
                if coefficient_unsigned < pow(2, coefficient_length - 1):
                    coefficient_signed = coefficient_unsigned - pow(2, coefficient_length) + 1
                else:
                    coefficient_signed = coefficient_unsigned
                # update the coefficient value in the acCoeff array with the correct value.
                channel.acCoeff[coefficient_read] = coefficient_signed
                # increment the coefficient read by 1 since a single coefficient is read. This is not a special symbol so no need to increment by 16 like 0xF0.
                coefficient_read += 1

                if coefficient_signed != 0 and coefficient_signed != 1:
                    self.Bits += 1
                #[END] for AC coefficients.
    
    def writeBlock(self, channel: Channel, bitwriter: BitWriter, isChrominance: bool) -> None:

        """USED TO HUFFMAN ENCODE THE BITSTREAM AS CODE - COEFFICIENT PAIRS."""
  
        # CodeWrapper is a helper class created to represent the code and code length.
        number_of_zeros = 0
        codeWrapper = CodeWrapper()

        # [START] - DC Coefficients
        coeff = channel.dcCoeff # gets the DC coefficient of the current channel.
        coeff_len = calculateCoeffLength(coeff) # calculates the minimum bits required to represent the coefficient length. Recall, lower 4 bits of a symbol is coeff length in bits.
        symbol = 0x00 | coeff_len # bitwise OR is used to create the symbol. Refer to dissertation, No zeros preceding a DC coefficient therefore run length is always 0 (0x00)
        self.header.generateSymbolCode(symbol, False, isChrominance, codeWrapper) # gets the code of the symbol. Code is stored inside the codeWrapper object that's why a parameter.
        bitwriter.write_code(codeWrapper.code, codeWrapper.length) # writes the code to the bitstream.

        # if DC coefficient is negative - its sign bit is set, adjusts the coefficient value.
        # JPEG uses modified form of twos complement representation for -ve values
        # -ve value is one less than the absolute value of the minimum positive value
        # eg: in 8 bit representation, max -ve value is -128 and min +ve val is +1, to represent -128
        # coeff value should be -127 - by subtracting 1 from the coefficient value if negative.
        if coeff < 0:
            coeff -= 1
        bitwriter.write_code(coeff, coeff_len) # writes DC coefficient to bitstream using coeff_len bits
        # [END] - DC Coefficients 

        # [START] - AC Coefficients
        for j in range(63):
            # takes the first AC coefficient following the DC coefficient. 
            coeff = channel.acCoeff[j]

            # if the 62th coefficient is 0, special end of block symbol (0x00) is used - refer to dissertation.
            if j == 62 and coeff == 0:
                self.header.generateSymbolCode(0x00, True, isChrominance, codeWrapper) # gets the code of 0x00, that's why first parameter is hardcoded.
                bitwriter.write_code(codeWrapper.code, codeWrapper.length) # writes the code to the bitstream in code length's bits.
                # end of block is reached, escape the function.
                break
            # if AC coefficient is not 62th coeff in the block but a 0, increments number of zeros
            elif coeff == 0:
                number_of_zeros += 1
            else:
                # Huffman coding can only compress 16 zeros at a time - refer to dissertation.
                # Upper 4 bits of a symbol (run length - preceding zeros) can only be 16 values
                while number_of_zeros >= 16:
                    # if there are 16 zeroes or more between the previous and current non-zero coefficient, process special symbol (0xF0) - that's why first parameter is hardcoded
                    self.header.generateSymbolCode(0xF0, True, isChrominance, codeWrapper) # gets the code of F0.
                    bitwriter.write_code(codeWrapper.code, codeWrapper.length) #  writes the code of 0xF0 symbol to the bitstream the in required length in bits.
                    number_of_zeros -= 16 # decrement 16 because F0 symbol is processed.

                # gets the bit length of non-zero coefficient.
                coeff_len = calculateCoeffLength(coeff)
                # creates a symbol by setting the upper 4 bits to the number of zeros preceding the coefficient and the lower 4 bits to the coefficient length in bits.
                symbol = (number_of_zeros << 4) | coeff_len
                self.header.generateSymbolCode(symbol, True, isChrominance, codeWrapper) # gets the code of symbol 
                bitwriter.write_code(codeWrapper.code, codeWrapper.length) # writes the code to the bitstream in length bits.

                # as explained above, for negative coefficients, the twos complement rule is applied.
                if coeff < 0:
                    coeff -= 1
                bitwriter.write_code(coeff, coeff_len)

                number_of_zeros = 0
        # [END] - AC Coefficients.
        
    def writeMCU(self, mcu: MinimumCodedUnit, bitwriter: BitWriter) -> None:
        # writes Minimum Coded Unit to the bitstream
        # calculates the number of luminance blocks and for each luminance block, encodes the block by calling writeBlock().
        number_of_luminance_components: int = self.header.components[0].horizontalSamplingFactor * self.header.components[0].verticalSamplingFactor
        for i in range(number_of_luminance_components):
            self.writeBlock(mcu.luminance[i], bitwriter, False)
        
        # Grayscale images (black and white), only have one colour component, YCBCR has more than once, so check is implemented if there are more than one colour component.
        # calls writeBlock on every chrominance component. There are up to 2 chrominance components (cb and cr) therefore manually calls [0] and [1]
        if self.header.startOfFrame.numOfComponents > 1:
            self.writeBlock(mcu.chrominance[0], bitwriter, True)
            self.writeBlock(mcu.chrominance[1], bitwriter, True)

    def readNextSymbol(self, bits: BitReader, huffmanTable: HuffmanTable) -> int:
        """READS THE SYMBOLS USED TO HUFFMAN CODE/COMPRESS THE BITSTREAM"""

        # Huffman coded bitstream represents symbols as code therefore this functino reads the symbol from the codes.
        # bits is a BitReader object that maintains the huffman coded bitstream.
        code: int = 0
        index: int = 0 # index of the code in the bitstream
        valid: bool = False # set to true when the code found is a valid code.
        length: int = 1 # code length - must be 1 minimum, it is impossible to have a code of 0 length.

        # huffman coding uses codes with a maximum length of 16 bits
        while(length <= 16 and not valid):
            code <<= 1 # bitwise shift to the left by 1. Making room for the next bit of the huffman code
            code |= bits.readNextBit() & 0x01 # appends least significant bit of the next huffman code to the right end of the code.
            start = huffmanTable.offsets[length -1] # retrieves the starting index in the huffman table for codes of length.
            mirror = pow(2, length) - 1 # gets the sequence of 'length' ones in binary form, used to compare the bits of the huffman codes.
            # iterates for the number of codes of specific length in bits - codes of length 2, 3 bits etc...  
            for i in range(start, huffmanTable.offsets[length]):
                # mirror extracts the lowest "length" bits the code we are reading and the huffman code at index i in codes array.
                # if the lengths match, index is used to access the huffman symbol at index i.
                if(code & mirror) == (huffmanTable.codes[i] & mirror):                    
                    valid = True
                    index = i
                    break
            # if the code lengths are not matching, the validity will stay False, length is incremented and reading iterates
            if not valid:
                length += 1
        
        # returns the huffman symbol in the respective huffman table by accessing index in symbols array which stores all the huffman symbols.
        return huffmanTable.symbols[index]

    def findAvailableCoeffExtract(self) -> int:
        # derivative of findAvailableCoeff(), see explanation there.
        coeff_value = self.findCoeffExtract()
        while coeff_value == 0 or coeff_value == 1:
            coeff_value = self.findCoeffExtract()
        return coeff_value

    def findCoeffExtract(self) -> int:
        """
        Derivation of findCoeff() function, just returns the coefficient value. No need to return, coefficient index, channel number, channel type, and MCU.
        We are not altering a coefficient, we are just extracting the coefficient value which will be used in retrieval to get the embedded secret message.
        """
        # to understand how this works, refer to findCoeff() function. No need to comment the same here.
        if self.currMCU >= len(self.MCUVector):
            raise RuntimeError("Index of coefficient read is out of range.")
        
        if self.ChannelType:
            coeff_value = self.MCUVector[self.currMCU].luminance[self.ChannelNumber].acCoeff[self.Coefficient]
        else:
            coeff_value = self.MCUVector[self.currMCU].chrominance[self.ChannelNumber].acCoeff[self.Coefficient]
        
        self.Coefficient += 1
        self.Coefficient %= 63 
        
        if self.Coefficient == 0:
            if self.ChannelType:
                self.ChannelNumber = (self.ChannelNumber + 1) % (self.header.components[0].horizontalSamplingFactor * self.header.components[0].verticalSamplingFactor)
                if self.ChannelNumber == 0:
                    self.ChannelType = False
            else:
                self.ChannelNumber = (self.ChannelNumber + 1) % 2
                if self.ChannelNumber == 0:
                    self.ChannelType = True
        
        if self.Coefficient == 0 and self.ChannelType and self.ChannelNumber == 0:
            self.currMCU += 1
        
        return coeff_value

    def findAvailableCoeff(self) -> tuple:
        
        # tuple contains the set of information that will be needed to update the coefficient value. - coefficient index in the block, value, channel type (lum/chr), current channel
        # to avoid embeding in the zero and one coefficients (JSTEG RULE), we check if val is 0 or 1, if so continue to find a coefficient that is not 0 or 1. Return the same tuple to injectFile()
        tup = self.findCoeff()
        while tup[1] == 0 or tup[1] == 1:
            tup = self.findCoeff() 
        return tup 

    def findCoeff(self) -> tuple:

        if self.currMCU >= len(self.MCUVector):
            raise RuntimeError("Index of coefficient read is out of range.")

        # channel type is boolean arbitrary - True = Luminance colour channel, False = Chrominance colour channel.
        if self.ChannelType:
            val = self.MCUVector[self.currMCU].luminance[self.ChannelNumber].acCoeff[self.Coefficient]
            idx = self.Coefficient
            ch = True
            channel = self.ChannelNumber
            mcu = self.currMCU

        else:
            val = self.MCUVector[self.currMCU].chrominance[self.ChannelNumber].acCoeff[self.Coefficient]
            idx = self.Coefficient
            ch = False
            channel = self.ChannelNumber
            mcu = self.currMCU

        # increments the current coefficient by 1 each time the tuple is returned. then checks if the end of the block is reached by taking the modulus of 63.
        # we only alter AC coefficients in each block, therefore modulus 63. Since there are 63 AC coefficients in each block.
        self.Coefficient += 1
        self.Coefficient %= 63

        # checks if the coefficient index is zero - start of the new 8x8 block
        # if it is, updates the channel number and channel type.
        # if the channel number is the last in the horizontal and vertical sampling factors of the luminance component, moves to next channel
        if self.Coefficient == 0:
            # If channel type is True - Luminance
            if self.ChannelType:
                self.ChannelNumber = (self.ChannelNumber + 1) % (self.header.components[0].horizontalSamplingFactor * self.header.components[0].verticalSamplingFactor)
                if self.ChannelNumber == 0:
                    self.ChannelType = False
            # Channel type is False - Chrominance
            else:
                self.ChannelNumber = (self.ChannelNumber + 1) % 2
                if self.ChannelNumber == 0:
                    self.ChannelType = True
        
        if self.Coefficient == 0 and self.ChannelNumber == 0 and self.ChannelType:
            self.currMCU += 1
        
        return (idx, val, ch, channel, mcu)
    
    def decodeMCU(self, mcu: MinimumCodedUnit, bit: BitReader, finalDcCoeff: int) -> None:
        """
        Decodes Minimum Coded Unit
        """
        # total luminance blocks is the luminance horizontal sampling factor * luminance vertical sampling factor
        # components[0] = luma, first component in YCbCr is Y - luma then Cb, Cr. 
        luminanceBlocks = self.header.components[0].horizontalSamplingFactor * self.header.components[0].verticalSamplingFactor
        for i in range(luminanceBlocks):
            # decodes each luminance block in mcu.luminance[]
            self.decodeBlock(mcu.luminance[i], bit, finalDcCoeff, self.header.dcHuffmanTables[self.header.components[0].dcHuffmanTableId], self.header.acHuffmanTables[self.header.components[0].acHuffmanTableId])
            # sets the DC coefficient of luma block to finalDcCoeff
            finalDcCoeff = mcu.luminance[i].dcCoeff

        # if image is not grayscale, total number of colour components is more than 1.
        # decodes each chroma block
        # decodes only twice because in an MCU there are 4 luma and 2 chroma channels.
        if self.header.startOfFrame.numOfComponents > 1:
            self.decodeBlock(mcu.chrominance[0], bit, finalDcCoeff, self.header.dcHuffmanTables[self.header.components[1].dcHuffmanTableId], self.header.acHuffmanTables[self.header.components[1].acHuffmanTableId])
            finalDcCoeff = mcu.chrominance[0].dcCoeff
            self.decodeBlock(mcu.chrominance[1], bit, finalDcCoeff, self.header.dcHuffmanTables[self.header.components[2].dcHuffmanTableId], self.header.acHuffmanTables[self.header.components[2].acHuffmanTableId])

    def extractFromJPG(self, secretData: bytearray) -> None:

        size_of_secret_file: int = 0
        coefficient_value = 0
        _byte = np.array(0x00).astype(dtype=np.uint32)

        for i in range(32):
            coefficient_value = self.findAvailableCoeffExtract()
            if coefficient_value is not None:
                coefficient_value_unsigned = np.array(coefficient_value).astype(dtype=np.uint32)
                
                size_of_secret_file = size_of_secret_file << 1

                coefficient_value_signed = np.array(coefficient_value_unsigned & 0x01).astype(dtype=np.int32)
                size_of_secret_file = size_of_secret_file | coefficient_value_signed
            else:
                break
            
        for i in range(1, ((size_of_secret_file * 8) + 1)):
            coefficient_value = self.findAvailableCoeffExtract()
            if coefficient_value is not None:
                coefficient_value_unsigned = np.array(coefficient_value).astype(dtype=np.uint32)
            
                _byte = _byte << 1
                coefficient_value_signed = np.array(coefficient_value_unsigned & 0x01).astype(dtype=np.int32)
                _byte = _byte | coefficient_value_signed

                if (i % 8 == 0):
                    secretData.append(_byte)
                    _byte = 0x00
            else:
                break

    def saveJPGData(self, name: str) -> None:
        '''
        Saves current JPEG image in to with the given name.
        + creates huffman tables for color components. (dc coefficients and ac coefficients use separate huffman tables.)
        + updates the dcHuffmanTables and acHuffmanTables of the header object with four huffman tables created.
        + creates new bitstream and adds the end of image marker bytes (FFD9) to the end of bitstream.
        + saves the new bitstream to a file with given name.
        '''
        # creating empty HuffmanTables that will be filled with standard data.
        dcLuminance = HuffmanTable()
        dcChrominance = HuffmanTable()
        acLuminance = HuffmanTable()
        acChrominance = HuffmanTable()
        
        optimizeHuffmanTable(dcLuminance, 'dc', 'lum')
        optimizeHuffmanTable(acLuminance, 'ac', 'lum')
        optimizeHuffmanTable(dcChrominance, 'dc', 'chr')
        optimizeHuffmanTable(acChrominance, 'ac', 'chr')

        # by standard, luminance tables get the ID 0, chrominance tables get the ID 1.
        self.header.dcHuffmanTables[0] = dcLuminance
        self.header.dcHuffmanTables[1] = dcChrominance
        self.header.acHuffmanTables[0] = acLuminance
        self.header.acHuffmanTables[1] = acChrominance

        # creating a byte array that will store the JPEG data in bytestream
        _bytes = bytearray()
        self.header.fillHeaderBytes(_bytes) # writes all the header data into the byte array the same way it is read initially.
        
        self.makeBitstream(_bytes) # encodes image data into bitstream using Huffman Coding and write it into the bytearray.
        _bytes.append(0xFF) 
        _bytes.append(0xD9) # adds the END OF IMAGE marker FFD9.
        writeToFile(name, _bytes) # saves the image. 
        #END of encoding.

    def makeBitstream(self, bitstream: bytearray) -> None:
        bitwriter = BitWriter()
        for i in range(len(self.MCUVector)): # iterates through each minimum coded unit in the MCU vector which contains image data divided into blocks
            self.writeMCU(self.MCUVector[i], bitwriter)
        
        bitwriter.add(bitstream) # adds the bitstream to the bitwriter object.

    def injectFile(self, filename: str) -> None:
        #opens the secretFile in binary mode, creates an immutable bytes object
        # file_data - immutable bytes object is converted to mutable bytearray object so that prepFileToInject() can add more bytes data.
        with open(filename, 'rb') as f:
            file_data = f.read()
            file_bytes = bytearray(file_data)
            
        # adds file size to the beginning of the bytearray and filename to the end.
        file_bytes = prepFileToInject(file_bytes, filename)
        if len(file_bytes) * 8 > self.Bits:
            raise RuntimeError(f'{os.path.basename(filename)} cannot be injected.')
        
        #creates a bitreader object from the secret file bytes.
        bitreader = BitReader(file_bytes)
        for i in range(len(file_bytes) * 8):
            tup = self.findAvailableCoeff()
            
            coefficient_index = tup[0]
            coefficient_value = tup[1]
            coefficient_value_unsigned = np.array(coefficient_value).astype(dtype=np.uint8) # the coefficient value is turned into an array of unsigned 8 bit integers. Otherwise bitwise logic can create bit overflows - producing a large integer coefficient.
            luminance = tup[2]
            channel = tup[3]
            mcu = tup[4]

            bit = bitreader.readNextBit()
            # [START] - LEAST SIGNIFICANT BIT STEGANOGRAPHY
            # If the bit value is 1, (true - arbitrary), changes the least significant bit (LSB) of the unsigned integer to 1. ELSE bit is 0, changes the LSB of the unsigned int to 0
            if bit:
                coefficient_value_unsigned = coefficient_value_unsigned | 0x01
            else:
                coefficient_value_unsigned = coefficient_value_unsigned & ~0x01

            # unsigned value is converted back to the signed value before updating the AC coefficient value in the 8x8 block.
            coefficient_value_signed = np.int8(coefficient_value_unsigned)
            # checks in the tuple (tup) if the channel of the AC coefficient is from the Luma or Chroma channel, then replaces the correct coefficient.
            if luminance:
                self.MCUVector[mcu].luminance[channel].acCoeff[coefficient_index] = coefficient_value_signed
            else:
                self.MCUVector[mcu].chrominance[channel].acCoeff[coefficient_index] = coefficient_value_signed

    def retrieveHiddenFile(self) -> None:
        data: bytearray = []
        self.extractFromJPG(data)
        filename = removeNameFromFileData(data)
        writeToFile(filename, bytes(data))

# used for debugging. No effect on both embed and retrieve
def printBlock(channel: Channel) -> None:
    print('DC: ', channel.dcCoeff)
    print('AC: ', end=" ")
    for coeff in channel.acCoeff:
        print(coeff, end=", ")

# used for debugging. No effect on both embed and retrieve
def printMCU(mcu: MinimumCodedUnit) -> None:
    for channel in mcu.luminance:
        printBlock(channel)
    for chrominance in mcu.chrominance:
        printBlock(chrominance)

def generateHuffmanCodes(huffmanTable: HuffmanTable) -> None:
    """
    Reads from the huffman table's offsets array to update its codes array
    """
    # initially code is 1 bit long so, 0 to begin with.
    code = 0 
    for offset in range(16):
        # for all code lengths from 1 - 16 where offset is current code length - 1 since offset is going from 0-15
        # when considering the current code length (offset + 1), we need to loop for total number of codes that are that length
        # huffmanTable.offsets[offset] gives starting index into the codes array of codes that are offset + 1 long
        for i in range(huffmanTable.offsets[offset], huffmanTable.offsets[offset + 1]):
            # takes the current code candidate and finalise it as a real code.
            huffmanTable.codes[i] = code
            # add 1 to the code candidate for the next code to be read.
            code += 1
        # everytime we move down the list (codes of len 1, codes of len 2, 3) etc, we have to increase the code length by appending a 0 to the right
        # this is done by binary shifting to the left by 1.
        code = code << 1

def calculateCoeffLength(coeff: int) -> int:
    
    # calculates the bits needed to represent the coefficient.
    # refer to dissertation, variable-length encoding stores the coefficient and run length as [(r,s)c]
    # where s is the number of bits to represent the coefficient. 

    len = 0 # number of bits required to represent coefficient is stored in len variable.
    
    # if coefficient is a zero, returns a 0    
    if coeff == 0:
        return 0
    # if coefficient is negative, first converts it to positive representation by multiplying with -1.
    # negative coefficients have different representations than positives
    if coeff < 0:
        coeff *= - 1
    
    # while coefficient is not zero, each time halving the coeff value. Halving the coefficient each time equals to shifting to the right by a bit each time.
    # each shift, increments length and halves the coeff value until it is zero. 
    # when zero is reached. loop exits and returns the minimum bit length needed to represent coefficient.
    while coeff:
        coeff //= 2
        len += 1

    return len

def prepFileToInject(filedata: bytearray, filename: str) -> bytearray:

    """
    organises the secret file to a specific format before hiding inside the JPEG. 
    filedata parameter is a bytearray - so it is mutable, originally it stores all the bytes in the file from start to end. 
    this function adds the file size to the beginning of the file with 4 consecutive bytes (the division of total file size to 4 bits), then adds the file basename from the full path to the end.
    this is done because the file size can be more than 255 - (the maximum byte value that can enter the bytearray), therefore it is divided to smaller chunks
    """
    # the file name is added the end of the file following a backslash. 
    # this name will be used to name the file when extracting it back.
    filename = os.path.basename(filename)
    filedata.append(ord('/'))

    # every character in the file is converted to ASCII representations, by passing the unicode value of the character into the byterray. Unicode is the integer representation in ASCII.
    for character in filename:
        filedata.append(ord(character)) # ord() returns the unicode number of the character.

    datasize = len(filedata) 
    # len(filedata) cannot be 0.
    if datasize < 0:
        raise ValueError(f'Secret file data size cannot be negative: {datasize}')
    else:
        # when datasize > 255, cannot add int value as byte - bytearray allows (0-255) only. & 0xFF masks out all the bits in the integer except the 8 least significant bits. 
        # eg. if datasize 645, bytearray(b'\x00\x00\x02\x85\<secretMessage>/filename')
        _byte = None
        for i in range(4):
            _byte = (datasize >> (8*i)) & 0xFF
            filedata.insert(0, _byte)
        return filedata

def optimizeHuffmanTable(huffman_table: HuffmanTable, type: str, component: str) -> None:

    """
    DECLARATION:
    The hardcoded data you see in this function is a standard. It does not differ.
    This must be the same because Huffman Table optimization must be done after the coefficients are altered.
    Steganography alters AC coefficients. These coefficients will have different lenghts in bits, so their symbols will be different than the original symbols.
    This changes the frequency distribution of symbols, meaning it will effect how the longer codes are assigned to rare occurring symbols and shorter codes will be assigned to more frequent symbols.
    For that we MUST NOT encode the tampered data with the original Huffman tables.

    For this reason new Huffman Tables must be created in this function. 
    Values you see in the tables below are according to the Joint Photographic Experts Group (JFIF) standard. 
    You can find it in Page 158, ANNEX K.3.3 in JFIF Specification by ITU T.81: https://www.w3.org/Graphics/JPEG/itu-t81.pdf

    """
    # there can only be two types of huffman tables 'dc' or 'ac' anything else is rejected.
    if type != 'dc' and type != 'ac':
        raise RuntimeError("Huffman table type is not 'ac' or 'dc'.")
    # there can only be two channels, chroma or luma, anything else is rejected.
    if component != 'lum' and component != 'chr':
        raise RuntimeError("Component can be either 'lum' (luminance) or 'chr' (chrominance)")
    
    # refering to dissertation, number of zeros preceding DC coefficients is always 0, so the upper 4 bits of the symbols is always 0.
    # the lower 4 bits of the DC symbols - length of DC coefficients in bits, can be between 0 and 11, so only 12 possible symbols can represent DC symbols
    # therefore dcSymbols array consists of only 12 Huffman symbols.
    dcSymbols = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B]
    acLuminanceSymbols = [
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11,
        0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71,
        0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
        0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52,
        0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18,
        0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37,
        0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56
        , 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75, 0x76
        , 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95
        , 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3
        , 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA
        , 0xD2 , 0xD3 , 0xD4 , 0xD5 , 0xD6 , 0xD7 , 0xD8 , 0xD9 , 0xDA , 0xE1 , 0xE2 , 0xE3 , 0xE4 , 0xE5 , 0xE6 , 0xE7
        , 0xE8 , 0xE9 , 0xEA , 0xF1 , 0xF2 , 0xF3 , 0xF4 , 0xF5 , 0xF6 , 0xF7 , 0xF8 , 0xF9 , 0xFA
    ]

    acChrominanceSymbols = [
        0x00, 0x01
        , 0x02
        , 0x03 , 0x11
        , 0x04 , 0x05 , 0x21 , 0x31
        , 0x06 , 0x12 , 0x41 , 0x51
        , 0x07 , 0x61 , 0x71
        , 0x13 , 0x22 , 0x32 , 0x81
        , 0x08 , 0x14, 0x42, 0x91, 0xA1,
        0xB1, 0xC1, 0x09, 0x23, 0x33, 0x52, 0xF0, 0x15, 0x62, 0x72
        ,0xD1, 0x0A, 0x16, 0x24, 0x34, 0xE1, 0x25, 0xF1, 0x17, 0x18
        ,0x19, 0x1A, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x35, 0x36, 0x37
        ,0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49
        ,0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63
        ,0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75
        ,0x76, 0x77, 0x78, 0x79, 0x7A, 0x82, 0x83, 0x84, 0x85, 0x86
        ,0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97
        ,0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8
        ,0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9
        ,0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA
        ,0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE2
        ,0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF2, 0xF3
        ,0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA
    ]
    # again since there are only 12 DC Huffman symbols, the remaining half are always 12.
    dcLuminanceOffsets = [0, 0, 1, 6, 7, 8, 9, 10, 11, 12, 12, 12, 12, 12, 12, 12, 12]
    dcChrominanceOffsets = [0, 0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12, 12, 12, 12, 12]
    # there are 162 possible Huffman symbols - refer to dissertation, so the ending entry in the offsets array is 162
    acLuminanceOffsets = [0, 0, 2, 3, 6, 9, 11, 15, 18, 23, 28, 32, 36, 36, 36, 37, 162]
    acChrominanceOffsets = [0, 0, 2, 3, 5, 9, 13, 16, 20, 27, 32, 36, 40, 40, 41, 43, 162]

    # checks if the table type parameter is DC, if so populates the huffman table symbols with 12 huffman symbols. by iterating 12 times.
    if type == 'dc':
        for i in range(12):
            huffman_table.symbols[i] = dcSymbols[i]
        
        # if color component the huffman table is used is luminance, the luminance offsets is used otherwise chrominance offsets is used.
        if component == 'lum':
            for i in range(17):
                huffman_table.offsets[i] = dcLuminanceOffsets[i]
        else:
            for i in range(17):
                huffman_table.offsets[i] = dcChrominanceOffsets[i]
    
    # checks table type is AC
    if type == 'ac':
        # if component is luminance
        if component == 'lum':
            # populates the huffman table symbols with the possible standard huffman table values by iterating 162 times
            for i in range(162):
                huffman_table.symbols[i] = acLuminanceSymbols[i]
            # populates the offsets array with all AC luminance offsets
            for i in range(17):
                huffman_table.offsets[i] = acLuminanceOffsets[i]
        # if component is chrominance
        else:
            # populates the huffman table with chrominance symbols
            for i in range(162):
                huffman_table.symbols[i] = acChrominanceSymbols[i]
            # populates the offsets array with chrominance offsets
            for i in range(17):
                huffman_table.offsets[i] = acChrominanceOffsets[i]

    # overwrites the huffman codes in the codes array of HuffmanTable object, with the new codes that will be created by the following function
    # this is necessary, otherwise the encoding will attempt Huffman encoding with original image tables which we MUST avoid.
    generateHuffmanCodes(huffman_table) 

def removeNameFromFileData(filedata: bytearray) -> str:

    file: str = ''
    idx: int = 0
    for i in range(len(filedata)-1, -1, -1):
        if filedata[i] == ord('/'):
            idx = i
            break
    
    if idx == 0:
        raise RuntimeError("Error - Could not remove the file name.")
    
    for i in range(idx + 1, len(filedata)):
        file += chr(filedata[i])
    
    del filedata[idx:len(filedata)]
    
    return file

def writeToFile(name: str, data: bytearray) -> None:
    with open(name, 'wb') as file:
        file.write(data)