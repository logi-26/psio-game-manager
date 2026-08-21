'''
Merges multiple BIN files into a single BIN file and generates a new CUE file
'''

# System imports
from os.path import exists, join


class BinMerger:
    """A class to handle merging BIN files and creating a merged CUE sheet for a game"""
    def __init__(self, debug_mode: bool = False):
        """Initialise the BinMerger"""
        self.debug_mode = debug_mode


    # ************************************************************************************
    def _debug_print(self, message: str):
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(message)
    # ************************************************************************************


    # ************************************************************************************
    def _sectors_to_cue_stamp(self, sectors: int):
        """Convert sectors to a CUE file timestamp (MM:SS:FF)"""
        minutes = sectors // 4500
        fields = sectors % 4500
        seconds = fields // 75
        fields = sectors % 75
        return '%02d:%02d:%02d' % (minutes, seconds, fields)
    # ************************************************************************************


    # ************************************************************************************
    def _create_merged_cuesheet(self, game_name: str, bin_files: list) -> str:
        """Creates a merged CUE file containing the multiple tracks"""
        cue_sheet = f'FILE "{game_name}.bin" BINARY\n'
        sector_pos = 0
        for bin_file in bin_files:
            for track in bin_file.get_tracks():
                track_number = self._pad_zero(track.get_track_number())
                cue_sheet += f'   TRACK {track_number} {track.get_track_type()}\n'

                for index in track.get_indexes():
                    index_offset = index["file_offset"]
                    sectors_to_cue_stamp = self._sectors_to_cue_stamp(sector_pos + index_offset)
                    index_id = self._pad_zero(index["id"])
                    cue_sheet += f'     INDEX {index_id} {sectors_to_cue_stamp}\n'

                sector_pos += bin_file.get_size() // track.get_block_size()

        return cue_sheet
    # ************************************************************************************


    # ************************************************************************************
    def _pad_zero(self, num: int) -> str:
        """Pad numbers below 10 with a zero"""
        return f"{num:02d}"
    # ************************************************************************************


    # ************************************************************************************
    def _merge_files(self, merged_bin_path: str, bin_files: list) -> bool:
        """Merges a list of BIN files into a single file"""

        if exists(merged_bin_path):
            self._debug_print(f"(Error) Target merged file already exists: {merged_bin_path}")
            return False

        # Track the offset for each BIN file
        offset = 0

        with open(merged_bin_path, 'wb') as outfile:
            # Loop through the BIN files
            for bin_file in bin_files:
                bin_file_name = bin_file.get_file_name()
                self._debug_print(f"Merging BIN file: {bin_file_name} at offset 0x{offset:X}")

                # Track size of current file
                file_size = 0

                with open(bin_file.get_file_path(), 'rb') as in_file:
                    while True:
                        chunk = in_file.read(1024 * 1024)
                        if not chunk:
                            break
                        outfile.write(chunk)
                        file_size += len(chunk)

                # Update offset after writing file
                offset += file_size

        return True
    # ************************************************************************************


    # ************************************************************************************
    def merge(self, game_name: str, cue_file_name: str, bin_files: list, out_dir: str) -> bool:
        """Main method to start the bin merging process"""
        self._debug_print("\nMerging BIN files...")

        # Return if the output directory does not exist
        if not exists(out_dir):
            self._debug_print(f'(ERROR) Output dir does not exist: {out_dir}')
            return False

        merged_cue_path = join(out_dir, cue_file_name)

        # Return if a merged CUE file already exists
        if exists(merged_cue_path):
            self._debug_print(f'(ERROR) Output CUE file already exists: {merged_cue_path}')
            return False

        # Create the merged CUE file content
        cue_sheet = self._create_merged_cuesheet(game_name, bin_files)

        # Merge the BIN files
        merged_bin_path = join(out_dir, game_name + '.bin')

        if not self._merge_files(merged_bin_path, bin_files):
            return False

        # Write the merged CUE file
        self._debug_print("Creating merged CUE file...")
        with open(merged_cue_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(cue_sheet)

        self._debug_print("BIN files have been merged")

        return True
    # ************************************************************************************
