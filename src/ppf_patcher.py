'''
Applies PPF patches to PlayStation BIN files
'''

# System imports
from os import SEEK_CUR, SEEK_END
from struct import unpack
from typing import BinaryIO, Optional, Tuple

class PPFProcessor:
    """Class to handle PPF patch file processing and application"""
    APPLY = 1
    UNDO = 2

    def __init__(self, debug_mode: bool = False):
        """Initialise PPFProcessor with optional debug mode"""
        self.debug_mode = debug_mode


    # ************************************************************************************
    def _debug_print(self, message: str) -> None:
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(message)
    # ************************************************************************************


    # ************************************************************************************
    def _show_file_id(self, ppf_file: BinaryIO, ppf_ver: int) -> int:
        """Extract and display the file ID from the PPF file"""
        len_idx = 4 if ppf_ver == 2 else 2

        ppf_file.seek(-(len_idx + 4), SEEK_END)
        id_magic = ppf_file.read(4).decode('ascii', errors='ignore')

        if id_magic != '.DIZ':
            return 0

        ppf_file.seek(-len_idx, SEEK_END)
        id_len = unpack(f'<{"I" if ppf_ver == 2 else "H"}', ppf_file.read(len_idx))[0]
        org_len = id_len

        id_len = min(id_len, 3072)
        ppf_file.seek(-(len_idx + 16 + id_len), SEEK_END)
        buffer = ppf_file.read(id_len).decode('ascii', errors='ignore')

        self._debug_print(f"available\n{buffer}")
        return org_len
    # ************************************************************************************


    # ************************************************************************************
    def open_files(self, bin_path: str, ppf_path: str) -> Optional[Tuple[BinaryIO, BinaryIO]]:
        """Opens the BIN/ISO and PPF files for patching"""
        self._debug_print(f"\nOpening bin file: {bin_path}")
        try:
            bin_file = open(bin_path, 'r+b')
        except OSError as error:
            print(f"(Error) cannot open file '{bin_path}': {error}")
            return None, None

        self._debug_print(f"Opening ppf file: {ppf_path}")
        try:
            ppf_file = open(ppf_path, 'rb')
        except OSError as error:
            print(f"(Error) cannot open file '{ppf_path}': {error}")
            bin_file.close()
            return None, None

        return bin_file, ppf_file
    # ************************************************************************************


    # ************************************************************************************
    def get_ppf_version(self, ppf_file: BinaryIO) -> int:
        """Checks the PPF version of the given PPF file"""
        ppf_file.seek(0)
        magic = ppf_file.read(4)
        magic_str = magic.decode('ascii', errors='ignore')

        if magic_str == 'PPF1':
            return 1
        elif magic_str == 'PPF2':
            return 2
        elif magic_str == 'PPF3':
            return 3
        else:
            print("(Error) patchfile is no PPF patch")
            return 0
    # ************************************************************************************


    # ************************************************************************************
    def is_ppf_patch_applied(self, bin_file: BinaryIO, ppf_file: BinaryIO) -> bool:
        """Checks if a PPF patch has already been applied to a BIN file by comparing bytes at patch offsets"""
        # Get PPF version
        ppf_ver = self.get_ppf_version(ppf_file)
        if ppf_ver == 0:
            print("(Error) Invalid PPF file")
            return False

        self._debug_print(f"Checking if PPF{ppf_ver}.0 patch is already applied...")

        # Initialise variables based on PPF version
        if ppf_ver == 1:
            # Start of patch data for PPF1
            ppf_file.seek(56)
            count = ppf_file.seek(0, SEEK_END) - 56
            seek_pos = 56
            # 32-bit offsets
            offset_size = 4
        elif ppf_ver == 2:
            ppf_file.seek(56)
            id_len = self._show_file_id(ppf_file, 2)
            seek_pos = 1084
            count = ppf_file.seek(0, SEEK_END) - seek_pos
            if id_len:
                count -= id_len + 38
            # 32-bit offsets
            offset_size = 4
        else:  # PPF3
            ppf_file.seek(57)
            block_check = ppf_file.read(1)[0]
            id_len = self._show_file_id(ppf_file, 3)
            seek_pos = 1084 if block_check else 60
            count = ppf_file.seek(0, SEEK_END) - seek_pos
            if id_len:
                count -= id_len + 18 + 16 + 2
            # 64-bit offsets
            offset_size = 8

        # Check each patch chunk
        while count > 0:
            ppf_file.seek(seek_pos)
            # Read offset (32-bit for PPF1/PPF2, 64-bit for PPF3)
            offset = unpack('<Q' if ppf_ver == 3 else '<I', ppf_file.read(offset_size))[0]

            # Number of bytes to patch
            anz = ppf_file.read(1)[0]

            # Bytes to compare
            patch_bytes = ppf_file.read(anz)

            # Read bytes from BIN file at the offset
            bin_file.seek(offset)
            bin_bytes = bin_file.read(anz)

            # Compare bytes
            if bin_bytes != patch_bytes:
                self._debug_print(
                    f"Mismatch at offset 0x{offset:08x}: "
                    f"Expected {patch_bytes.hex()}, Found {bin_bytes.hex()}"
                )
                return False

            self._debug_print(
                f"Match at offset 0x{offset:08x}: {patch_bytes.hex()}"
            )

            # Update counters
            seek_pos += offset_size + 1 + anz
            count -= offset_size + 1 + anz

            # Skip the undo data in PPF3 patch files if present
            if ppf_ver == 3:
                ppf_file.seek(anz, SEEK_CUR)
                count -= anz

        self._debug_print("All patch bytes match. Patch is already applied.")
        return True
    # ************************************************************************************


    # ************************************************************************************
    def apply_ppf1_patch(self, ppf_file: BinaryIO, bin_file: BinaryIO):
        """Applies a PPF1.0 patch"""
        ppf_file.seek(6)
        desc = ppf_file.read(50).decode('ascii', errors='ignore')

        self._debug_print("Patch-file is a PPF1.0 patch. Patch Information:")
        self._debug_print(f"Description: {desc}")

        ppf_file.seek(0, SEEK_END)
        count = ppf_file.tell() - 56
        seek_pos = 56
        self._debug_print("Patching... ")

        while count > 0:
            ppf_file.seek(seek_pos)
            offset = unpack('<I', ppf_file.read(4))[0]
            anz = ppf_file.read(1)[0]
            ppf_mem = ppf_file.read(anz)
            bin_file.seek(offset)

            self._debug_print(f"Writing Bytes: {ppf_mem.hex()} at Offset: 0x{offset:08x}")
            bin_file.write(ppf_mem)
            seek_pos += 5 + anz
            count -= 5 + anz

        self._debug_print("\nPatching Completed.\n")
    # ************************************************************************************


    # ************************************************************************************
    def apply_ppf2_patch(self, ppf_file: BinaryIO, bin_file: BinaryIO):
        """Applies a PPF2.0 patch"""
        ppf_file.seek(6)
        desc = ppf_file.read(50).decode('ascii', errors='ignore')

        self._debug_print("Patch-file is a PPF2.0 patch. Patch Information:")
        self._debug_print(f"Description: {desc}")

        id_len = self._show_file_id(ppf_file, 2)
        if not id_len:
            self._debug_print("not available")

        ppf_file.seek(56)
        obin_len = unpack('<I', ppf_file.read(4))[0]

        bin_file.seek(0, SEEK_END)
        bin_len = bin_file.tell()
        if obin_len != bin_len:
            self._debug_print("(Warning) The size of the bin file isn't correct, continuing anyway")

        ppf_file.seek(60)
        ppf_block = ppf_file.read(1024)
        bin_file.seek(0x9320)
        bin_block = bin_file.read(1024)

        if ppf_block != bin_block:
            self._debug_print("(Warning) Binblock/Patchvalidation failed, continuing anyway")

        ppf_file.seek(0, SEEK_END)
        count = ppf_file.tell()
        seek_pos = 1084
        count -= 1084
        if id_len:
            count -= id_len + 38
        self._debug_print("Patching... ")

        while count > 0:
            ppf_file.seek(seek_pos)
            offset = unpack('<I', ppf_file.read(4))[0]
            anz = ppf_file.read(1)[0]
            ppf_mem = ppf_file.read(anz)
            bin_file.seek(offset)

            self._debug_print(f"Writing Bytes: {ppf_mem.hex()} at Offset: 0x{offset:08x}")
            bin_file.write(ppf_mem)
            seek_pos += 5 + anz
            count -= 5 + anz

        self._debug_print("\nPatching Completed.\n")
    # ************************************************************************************


    # ************************************************************************************
    def apply_ppf3_patch(self, ppf_file: BinaryIO, bin_file: BinaryIO, mode: int = 1):
        """Applies or undoes a PPF3.0 patch"""
        ppf_file.seek(6)
        desc = ppf_file.read(50).decode('ascii', errors='ignore')

        self._debug_print("Patchfile is a PPF3.0 patch. Patch Information:")
        self._debug_print(f"Description: {desc}")

        id_len = self._show_file_id(ppf_file, 3)
        if not id_len:
            self._debug_print("not available")

        ppf_file.seek(56)
        image_type = ppf_file.read(1)[0]
        ppf_file.seek(57)
        block_check = ppf_file.read(1)[0]
        ppf_file.seek(58)
        undo = ppf_file.read(1)[0]

        if mode == self.UNDO and not undo:
            self._debug_print("(Error) no undo data available")
            return

        if block_check:
            ppf_file.seek(60)
            ppf_block = ppf_file.read(1024)
            bin_file.seek(0x80A0 if image_type else 0x9320)
            bin_block = bin_file.read(1024)

            if ppf_block != bin_block:
                self._debug_print("(Warning) Binblock/Patchvalidation failed, continuing anyway")

        ppf_file.seek(0, SEEK_END)
        count = ppf_file.tell()
        seek_pos = 1084 if block_check else 60
        count -= seek_pos
        if id_len:
            count -= (id_len + 18 + 16 + 2)

        ppf_file.seek(seek_pos)
        self._debug_print("Patching ... ")

        while count > 0:
            offset = unpack('<Q', ppf_file.read(8))[0]
            anz = ppf_file.read(1)[0]

            if mode == self.UNDO:
                ppf_file.seek(anz, SEEK_CUR)
                ppf_mem = ppf_file.read(anz)
            else:
                ppf_mem = ppf_file.read(anz)
                if undo:
                    ppf_file.seek(anz, SEEK_CUR)

            self._debug_print(f"Writing Bytes: {ppf_mem.hex()} at Offset: 0x{offset:08x}")
            bin_file.seek(offset)
            bin_file.write(ppf_mem)
            count -= (anz + 9)
            if undo:
                count -= anz

        self._debug_print("\nPatching Completed.\n")
    # ************************************************************************************
