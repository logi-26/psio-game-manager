from os import SEEK_CUR, SEEK_END
from struct import unpack

# Constants
APPLY = 1
UNDO = 2


# ************************************************************************************
def open_files_for_patching(bin_path: str, ppf_path: str):
    ''' Opens the BIN/ISO and PPF files for patching'''

    # Open BIN/ISO in read/write binary mode
    print(f"Opening bin file: {bin_path}")
    try:
        bin_file = open(bin_path, 'r+b')
    except OSError as e:
        print(f"Error: cannot open file '{bin_path}': {e}")
        return None, None

    # Open PPF patch file in read-only binary mode
    print(f"Opening ppf file: {ppf_path}")
    try:
        ppf_file = open(ppf_path, 'rb')
    except OSError as e:
        print(f"Error: cannot open file '{ppf_path}': {e}")
        bin_file.close()
        return None, None

    print(f"Files opened successfully: bin_fd={bin_file.fileno()}, ppf_fd={ppf_file.fileno()}")
    return bin_file, ppf_file
# ************************************************************************************


# ************************************************************************************
def ppf_version(ppf_file):
    ''' Checks the PPF version of the given PPF file'''

    # Read the first 4-bytes of the PPF patch file
    ppf_file.seek(0)
    magic = ppf_file.read(4)

    # Check if it is a PPF1, PPF2 or PPF3 file
    magic_str = magic.decode('ascii', errors='ignore')
    if magic_str == 'PPF1':
        print("Detected PPF1.0")
        return 1
    elif magic_str == 'PPF2':
        print("Detected PPF2.0")
        return 2
    elif magic_str == 'PPF3':
        print("Detected PPF3.0")
        return 3
    else:
        print("Error: patchfile is no PPF patch")
        return 0
# ************************************************************************************


# ************************************************************************************
def apply_ppf1_patch(ppf_file, bin_file):
    ''' 
    Applies a PPF1.0 patch
    Consists of:
    - 6-bytes PPF version number, 
    - 50-byte description
    - Remaining bytes is the patch data
    '''

    # Read the description from the PPF file
    ppf_file.seek(6)
    desc = ppf_file.read(50).decode('ascii', errors='ignore')

    # Print the patch details
    print("Patchfile is a PPF1.0 patch. Patch Information:")
    print(f"Description: {desc}")
    print("File_id.diz: no")

    # Skip the 56 byte header and seek to the patch data
    ppf_file.seek(0, SEEK_END)
    count = ppf_file.tell() - 56
    seekpos = 56
    print("Patching... ", end="", flush=True)

    # Apply the patch
    while count > 0:
        print("reading...\b\b\b\b\b\b\b\b\b\b", end="", flush=True)
        ppf_file.seek(seekpos)
        pos = unpack('<I', ppf_file.read(4))[0]     # Read 4-byte position
        anz = ppf_file.read(1)[0]                   # Read 1-byte length
        ppfmem = ppf_file.read(anz)                 # Read patch data
        bin_file.seek(pos)
        print("writing...\b\b\b\b\b\b\b\b\b\b", end="", flush=True)
        bin_file.write(ppfmem)
        seekpos += 5 + anz
        count -= 5 + anz

    print("successful.")
# ************************************************************************************


# ************************************************************************************
def apply_ppf2_patch(ppf_file, bin_file):
    ''' 
    Applies a PPF2.0 patch
    Consists of:
    - 6-bytes PPF version number, 
    - 50-byte description, 
    - 4-bytes bin file size, 
    - 1024-byte block-check
    - Remaining bytes is the patch data
    '''

    # Read the description from the PPF file
    ppf_file.seek(6)
    desc = ppf_file.read(50).decode('ascii', errors='ignore')

    # Print the patch details
    print("Patchfile is a PPF2.0 patch. Patch Information:")
    print(f"Description: {desc}")
    print("File_id.diz: ", end="")

    idlen = show_file_id(ppf_file, 2)
    if not idlen:
        print("not available")

    # Get the expected bin size from the PPF patch file
    ppf_file.seek(56)
    obinlen = unpack('<I', ppf_file.read(4))[0]

    # Check the size of the bin file
    bin_file.seek(0, SEEK_END)
    binlen = bin_file.tell()
    if obinlen != binlen:
        print("Warning: The size of the bin file isn't correct, continuing anyway")

    # Read the 1024-byte block-data from the PPF patch file
    ppf_file.seek(60)
    ppfblock = ppf_file.read(1024)

    # Read the 1024-byte block-data from the BIN file
    bin_file.seek(0x9320)
    binblock = bin_file.read(1024)

    # Compare the 1024-byte block data from the PPF patch file with the block of data from the BIN file
    if ppfblock != binblock:
        print("Warning: Binblock/Patchvalidation failed, continuing anyway")

    # Skip the header and block-check data and seek to the patch data
    ppf_file.seek(0, SEEK_END)
    count = ppf_file.tell()
    seekpos = 1084
    count -= 1084
    if idlen:
        count -= idlen + 38
    print("Patching... ", end="", flush=True)

    # Apply the patch
    while count > 0:
        print("reading...\b\b\b\b\b\b\b\b\b\b", end="", flush=True)
        ppf_file.seek(seekpos)
        pos = unpack('<I', ppf_file.read(4))[0]
        anz = ppf_file.read(1)[0]
        ppfmem = ppf_file.read(anz)
        bin_file.seek(pos)
        print("writing...\b\b\b\b\b\b\b\b\b\b", end="", flush=True)
        bin_file.write(ppfmem)
        seekpos += 5 + anz
        count -= 5 + anz

    print("successful.")
# ************************************************************************************


# ************************************************************************************
# Applies a PPF3.0 patch
def apply_ppf3_patch(ppf_file, bin_file, mode: int = 1):
    ''' 
    Applies or undoes a PPF3.0 patch
    mode: 1=apply patch, 2=undo patch
    Consists of:
    - 6-bytes PPF version number, 
    - 50-byte description,
    - 1-byte image type (0=ISO, 1=BIN),
    - 1-byte block-check present (0=no, 1=yes),
    - 1-byte undo data present (0=no, 1=yes),
    - 1024-byte block-check (if present),
    - Remaining bytes is the patch data
    '''

    # Read the description from the PPF file
    ppf_file.seek(6)
    desc = ppf_file.read(50).decode('ascii', errors='ignore')

    # Print the patch details
    print("Patchfile is a PPF3.0 patch. Patch Information:")
    print(f"Description: {desc}")
    print("File_id.diz: ", end="")

    idlen = show_file_id(ppf_file, 3)
    if not idlen:
        print("not available")

    # Read the image type (BIN or ISO)
    ppf_file.seek(56)
    imagetype = ppf_file.read(1)[0]

    # Check if block-check data is included in the PPF file
    ppf_file.seek(57)
    blockcheck = ppf_file.read(1)[0]

    # Check if the PPF file is able to undo the changes applied by the patch
    ppf_file.seek(58)
    undo = ppf_file.read(1)[0]

    # If mode is set to undo but the PPF file does not contain any patch removal data
    if mode == UNDO and not undo:
        print("Error: no undo data available")
        return

    # If the PPF patch file does contain block-check data
    if blockcheck:
        # Read the 1024-byte block-data from the PPF patch file
        ppf_file.seek(60)
        ppfblock = ppf_file.read(1024)

        # Seek to the correct offset for BIN or ISO file
        bin_file.seek(0x80A0 if imagetype else 0x9320)

        # Read the 1024-byte block-data from the BIN/ISO file
        binblock = bin_file.read(1024)

        # Compare the 1024-byte block data from the PPF patch file with the data from the BIN/ISO file
        if ppfblock != binblock:
            print("Warning: Binblock/Patchvalidation failed, continuing anyway")

    # Get the PPF patch file size
    ppf_file.seek(0, SEEK_END)
    count = ppf_file.tell()

    # Seek to the correct offset in the PPF patch file depending if the block-check is present
    seekpos = 1084 if blockcheck else 60
    count -= seekpos
    if idlen:
        count -= (idlen + 18 + 16 + 2)

    # Skip the header and block-check data and seek to the patch data
    ppf_file.seek(seekpos)
    print("Patching ... ", end="", flush=True)

    while count > 0:
        print("reading...\b\b\b\b\b\b\b\b\b\b", end="", flush=True)
        offset = unpack('<Q', ppf_file.read(8))[0]  # Read 8-byte offset
        anz = ppf_file.read(1)[0]

        # Apply or undo the patch to the BIN/ISO file
        if mode == APPLY:
            ppfmem = ppf_file.read(anz)
            if undo:
                ppf_file.seek(anz, SEEK_CUR)
        elif mode == UNDO:
            ppf_file.seek(anz, SEEK_CUR)
            ppfmem = ppf_file.read(anz)

        print("writing...\b\b\b\b\b\b\b\b\b\b", end="", flush=True)
        bin_file.seek(offset)
        bin_file.write(ppfmem)
        count -= (anz + 9)
        if undo:
            count -= anz

    print("successful.")
# ************************************************************************************


# ************************************************************************************
# Shows File_Id.diz of a PPF2.0 / PPF3.0 patch
def show_file_id(ppf_file, ppfver: int):
    lenidx = 4 if ppfver == 2 else 2
    ppf_file.seek(-(lenidx + 4), SEEK_END)
    idmagic = ppf_file.read(4).decode('ascii', errors='ignore')

    if idmagic != '.DIZ':
        return 0

    ppf_file.seek(-lenidx, SEEK_END)
    idlen = unpack(f'<{"I" if ppfver == 2 else "H"}', ppf_file.read(lenidx))[0]
    orglen = idlen

    if idlen > 3072:
        idlen = 3072

    ppf_file.seek(-(lenidx + 16 + idlen), SEEK_END)
    buffer = ppf_file.read(idlen).decode('ascii', errors='ignore')

    print(f"available\n{buffer}")
    return orglen
# ************************************************************************************
