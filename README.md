# Vault - Steganography Tool

Vault is a tool written in Python to allow its users to embed and extract secret text files from a cover image. 

The functionality of Vault derives from reading information from .jpg images and writing information to its bitstream.
JPG images consist of an header and a bitstream. The header contains metadata about the image and relevant processings it has been through.
Precisely, the header includes marker segments. Each marker segment contains information specific about JPG components.

 ## Components of Vault:
+ jpeg.py: implements reading from image and writing into image
+ parser.py: implements command line argument parser
+ reader.py: implements reading individual bits from binary data
+ steg.py: implements steganography
+ vault.py: implements command line argument parser
+ writer.py: implements writing individual bits from binary data

## Command Line Argument Usage:
Options:
+ --embed: hides text into image (mutually exclusive)
+ --recover: extracts text from image (mutually exclusive)

Positional Arguments:
+ cover image: path to the image file
+ text file: path to the text file
+ stego image: path to stego image 

To be developed:
+ JSteg or F5 Steganographic algorithm (embedding and retrieval)
+ Stego key for the encryption of secret text inside the image
+ Use logging instead of printing outputs.