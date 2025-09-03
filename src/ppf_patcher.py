from os import SEEK_CUR, SEEK_END
from struct import unpack
from typing import BinaryIO

# Constants
DEBUG_MODE = False
APPLY = 1
UNDO = 2


# ************************************************************************************
def set_ppf_debug_mode(debug_mode: bool):
    """Set the debug mode"""
    global DEBUG_MODE
    DEBUG_MODE = debug_mode
# ************************************************************************************


# ************************************************************************************
def open_files_for_patching(bin_path: str, ppf_path: str):
    """Opens the BIN/ISO and PPF files for patching"""

    # Open BIN/ISO in read/write binary mode
    _debug_print(f"\nOpening bin file: {bin_path}")
    try:
        bin_file = open(bin_path, 'r+b')
    except OSError as error:
        print(f"Error: cannot open file '{bin_path}': {error}")
        return None, None

    # Open PPF patch file in read-only binary mode
    _debug_print(f"Opening ppf file: {ppf_path}")
    try:
        ppf_file = open(ppf_path, 'rb')
    except OSError as error:
        print(f"Error: cannot open file '{ppf_path}': {error}")
        bin_file.close()
        return None, None

    return bin_file, ppf_file
# ************************************************************************************


# ************************************************************************************
def ppf_version(ppf_file: BinaryIO) -> int:
    """Checks the PPF version of the given PPF file"""

    # Read the first 4-bytes of the PPF patch file
    ppf_file.seek(0)
    magic = ppf_file.read(4)

    # Check if it is a PPF1, PPF2 or PPF3 file
    magic_str = magic.decode('ascii', errors='ignore')
    if magic_str == 'PPF1':
        return 1
    elif magic_str == 'PPF2':
        return 2
    elif magic_str == 'PPF3':
        return 3
    else:
        print("Error: patchfile is no PPF patch")
        return 0
# ************************************************************************************


# ************************************************************************************
def apply_ppf1_patch(ppf_file: BinaryIO, bin_file: BinaryIO):
    """ 
    Applies a PPF1.0 patch
    Consists of:
    - 6-bytes PPF version number, 
    - 50-byte description
    - Remaining bytes is the patch data
    """

    # Read the description from the PPF file
    ppf_file.seek(6)
    desc = ppf_file.read(50).decode('ascii', errors='ignore')

    # Print the patch details
    _debug_print("Patch-file is a PPF1.0 patch. Patch Information:")
    _debug_print(f"Description: {desc}")

    # Skip the 56 byte header and seek to the patch data
    ppf_file.seek(0, SEEK_END)
    count = ppf_file.tell() - 56
    seek_pos = 56
    _debug_print("Patching... ")

    # Apply the patch
    while count > 0:
        ppf_file.seek(seek_pos)
        offset = unpack('<I', ppf_file.read(4))[0]      # Read 4-byte position
        anz = ppf_file.read(1)[0]                       # Read 1-byte length
        ppf_mem = ppf_file.read(anz)                    # Read patch data
        bin_file.seek(offset)

        _debug_print(f"Writing Bytes: {ppf_mem.hex()} at Offset: 0x{offset:08x}")
        bin_file.write(ppf_mem)
        seek_pos += 5 + anz
        count -= 5 + anz

    _debug_print("\nPatching Completed.\n")
# ************************************************************************************


# ************************************************************************************
def apply_ppf2_patch(ppf_file: BinaryIO, bin_file: BinaryIO):
    """ 
    Applies a PPF2.0 patch
    Consists of:
    - 6-bytes PPF version number, 
    - 50-byte description, 
    - 4-bytes bin file size, 
    - 1024-byte block-check
    - Remaining bytes is the patch data
    """

    # Read the description from the PPF file
    ppf_file.seek(6)
    desc = ppf_file.read(50).decode('ascii', errors='ignore')

    # Print the patch details
    _debug_print("Patch-file is a PPF2.0 patch. Patch Information:")
    _debug_print(f"Description: {desc}")

    id_len = _show_file_id(ppf_file, 2)
    if not id_len:
        _debug_print("not available")

    # Get the expected bin size from the PPF patch file
    ppf_file.seek(56)
    obin_len = unpack('<I', ppf_file.read(4))[0]

    # Check the size of the bin file
    bin_file.seek(0, SEEK_END)
    bin_len = bin_file.tell()
    if obin_len != bin_len:
        _debug_print("Warning: The size of the bin file isn't correct, continuing anyway")

    # Read the 1024-byte block-data from the PPF patch file
    ppf_file.seek(60)
    ppf_block = ppf_file.read(1024)

    # Read the 1024-byte block-data from the BIN file
    bin_file.seek(0x9320)
    bin_block = bin_file.read(1024)

    # Compare the 1024-byte block data from the PPF patch file with the block of data from the BIN file
    if ppf_block != bin_block:
        _debug_print("Warning: Binblock/Patchvalidation failed, continuing anyway")

    # Skip the header and block-check data and seek to the patch data
    ppf_file.seek(0, SEEK_END)
    count = ppf_file.tell()
    seek_pos = 1084
    count -= 1084
    if id_len:
        count -= id_len + 38
    _debug_print("Patching... ")

    # Apply the patch
    while count > 0:
        ppf_file.seek(seek_pos)
        offset = unpack('<I', ppf_file.read(4))[0]
        anz = ppf_file.read(1)[0]
        ppf_mem = ppf_file.read(anz)
        bin_file.seek(offset)

        _debug_print(f"Writing Bytes: {ppf_mem.hex()} at Offset: 0x{offset:08x}")
        bin_file.write(ppf_mem)
        seek_pos += 5 + anz
        count -= 5 + anz

    _debug_print("\nPatching Completed.\n")
# ************************************************************************************


# ************************************************************************************
def apply_ppf3_patch(ppf_file: BinaryIO, bin_file: BinaryIO, mode: int = 1):
    """ 
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
    """

    # Read the description from the PPF file
    ppf_file.seek(6)
    desc = ppf_file.read(50).decode('ascii', errors='ignore')

    # Print the patch details
    _debug_print("Patchfile is a PPF3.0 patch. Patch Information:")
    _debug_print(f"Description: {desc}")

    id_len = _show_file_id(ppf_file, 3)
    if not id_len:
        _debug_print("not available")

    # Read the image type (BIN or ISO)
    ppf_file.seek(56)
    image_type = ppf_file.read(1)[0]

    # Check if block-check data is included in the PPF file
    ppf_file.seek(57)
    block_check = ppf_file.read(1)[0]

    # Check if the PPF file is able to undo the changes applied by the patch
    ppf_file.seek(58)
    undo = ppf_file.read(1)[0]

    # If mode is set to undo but the PPF file does not contain any patch removal data
    if mode == UNDO and not undo:
        _debug_print("Error: no undo data available")
        return

    # If the PPF patch file does contain block-check data
    if block_check:
        # Read the 1024-byte block-data from the PPF patch file
        ppf_file.seek(60)
        ppf_block = ppf_file.read(1024)

        # Seek to the correct offset for BIN or ISO file
        bin_file.seek(0x80A0 if image_type else 0x9320)

        # Read the 1024-byte block-data from the BIN/ISO file
        bin_block = bin_file.read(1024)

        # Compare the 1024-byte block data from the PPF patch file with the data from the BIN/ISO file
        if ppf_block != bin_block:
            _debug_print("Warning: Binblock/Patchvalidation failed, continuing anyway")

    # Get the PPF patch file size
    ppf_file.seek(0, SEEK_END)
    count = ppf_file.tell()

    # Seek to the correct offset in the PPF patch file depending if the block-check is present
    seek_pos = 1084 if block_check else 60
    count -= seek_pos
    if id_len:
        count -= (id_len + 18 + 16 + 2)

    # Skip the header and block-check data and seek to the patch data
    ppf_file.seek(seek_pos)
    _debug_print("Patching ... ")

    while count > 0:
        offset = unpack('<Q', ppf_file.read(8))[0]  # Read 8-byte offset
        anz = ppf_file.read(1)[0]

        # Apply or undo the patch to the BIN/ISO file
        if mode == UNDO:
            ppf_file.seek(anz, SEEK_CUR)
            ppf_mem = ppf_file.read(anz)
        else:
            ppf_mem = ppf_file.read(anz)
            if undo:
                ppf_file.seek(anz, SEEK_CUR)

        _debug_print(f"Writing Bytes: {ppf_mem.hex()} at Offset: 0x{offset:08x}")
        bin_file.seek(offset)
        bin_file.write(ppf_mem)
        count -= (anz + 9)
        if undo:
            count -= anz

    _debug_print("\nPatching Completed.\n")
# ************************************************************************************


# ************************************************************************************
def _show_file_id(ppf_file: BinaryIO, ppf_ver: int) -> int:
    """Extract and display the file ID from the PPF file"""

    len_idx = 4 if ppf_ver == 2 else 2

    ppf_file.seek(-(len_idx + 4), SEEK_END)
    id_magic = ppf_file.read(4).decode('ascii', errors='ignore')

    if id_magic != '.DIZ':
        return 0

    ppf_file.seek(-len_idx, SEEK_END)
    id_len = unpack(f'<{"I" if ppf_ver == 2 else "H"}', ppf_file.read(len_idx))[0]
    org_len = id_len

    # Limit the length to avoid excessive memory usage
    id_len = min(id_len, 3072)

    ppf_file.seek(-(len_idx + 16 + id_len), SEEK_END)
    buffer = ppf_file.read(id_len).decode('ascii', errors='ignore')

    _debug_print(f"available\n{buffer}")
    return org_len
# ************************************************************************************


# ************************************************************************************
def _debug_print(message: str):
    """Print debug messages if debug mode is enabled"""
    if DEBUG_MODE:
        print(message)
# ************************************************************************************
