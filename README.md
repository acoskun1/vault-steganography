# Vault - Steganography Tool

## Components of Vault:

### frontend/ (ignore it.)
+ Ignore frontend/. Front end attempted but not connected to backend. Not functional.
+ Agreed by both first and second markers it is not mandatory to implement frontend since software of similar domain are based on command line interface.

### backend/
+ jpeg.py: implements decoding and encoding JPG
+ vault.py: implements command line argument parser
+ reader.py: implements reading bits from binary data
+ writer.py: implements writing bits from binary data
***
## How Vault works:
While embedding you must specify three parameters "path_to_cover_image", "path_to_secret_text", "path_to_where_stego_image_written".

While retrieving you must only specify path to the stego image from which the secret text will be extracted.

If embedding is successful, stego image will be saved to the location you have specified.

If retrieval is successful, secret text will be saved to your current directory.
***
## Command Line Argument Usage:
Optional Arguments:
+ --embed: hides text into image (mutually exclusive) - mode group | NO ABBREVIATIONS ACCEPTED (eg: -e or -emb)
+ --retrieve: extracts text from image (mutually exclusive) - mode group | NO ABBREVIATIONS ACCEPTED (eg: -r or -ret)
+ -m, --meta-data: prints out metadata of decoded image

Positional Arguments:
+ cover image: path to the image file
+ secret file: path to the secret file
+ stego image: path to where the stego image will be saved 

You can also run python3 vault.py --help to see all.
***
## How to run the program?
When running the program, you must be located inside the backend directory or calling vault.py from the location it is in.

Embed:<br>
if inside /stegvalet/backend/
+ python3 vault.py --embed path/to/cover/image  path/to/secret/file/  path/to/stego/image/written

if outside of backend:
+ python3 path/to/stegvalet/vault.py --embed path/to/cover/image  path/to/secret/file/  path/to/stego/image/written

Retrieve:<br>
if inside /stegvalet/backend/
+ python3 vault.py --retrieve path/to/stego/image/

if outside of backend:
+ python3 path/to/stegvalet/vault.py --retrieve path/to/stego/image/
***

