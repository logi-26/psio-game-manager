'''
Generates a CU2 file from a PlayStation CUE file
'''

from os.path import exists, join, getsize
from pathlib import Path
from typing import Optional
from re import compile, IGNORECASE


class Cu2Generator:
    """A class to convert CUE sheet's to CU2"""

    _RE_MODE2 = compile(r'.*mode2/2352.*', IGNORECASE)
    _RE_TRACK = compile(r'[ \t]*track.*', IGNORECASE)
    _RE_FILE_TRACK = compile(r'[ \t]*file.*track.*', IGNORECASE)
    _RE_INDEX_00 = compile(r'.*index\s+0?0\b.*', IGNORECASE)
    _RE_INDEX_01 = compile(r'.*index\s+0?1\b.*', IGNORECASE)

    def __init__(self, debug_mode: bool = False):
        """Initialise the CueConverter"""
        self.debug_mode = debug_mode

        # Hardcoded for CU2 revision 2
        self.format_revision = 2

    # ************************************************************************************
    def _debug_print(self, message: str):
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(message)
    # ************************************************************************************


    # ************************************************************************************
    def _timecode_to_sectors(self, time_code: str) -> int:
        """Convert time code to sectors"""
        minutes = int(time_code[0:2])
        seconds = int(time_code[3:5])
        sectors = int(time_code[6:8])
        minutes_sectors = int(minutes * 60 * 75)
        seconds_sectors = int(seconds * 75)
        return minutes_sectors + seconds_sectors + sectors
    # ************************************************************************************


    # ************************************************************************************
    def _sectors_to_timecode(self, sectors: int) -> str:
        """Convert sectors to time code"""
        total_seconds = sectors // 75
        modulo_sectors = sectors % 75
        total_minutes = total_seconds // 60
        modulo_seconds = total_seconds % 60
        return f'{total_minutes:02d}:{modulo_seconds:02d}:{modulo_sectors:02d}'
    # ************************************************************************************


    # ************************************************************************************
    def _sectors_to_timecode_alternative(self, sectors: int) -> str:
        """Convert sectors to time code, using MM:SS-1:75 instead of MM:SS:00"""
        total_seconds = sectors // 75
        modulo_sectors = sectors % 75
        total_minutes = total_seconds // 60
        modulo_seconds = total_seconds % 60

        if modulo_sectors == 0:
            modulo_sectors = 75
            modulo_seconds = modulo_seconds - 1 if modulo_seconds != 0 else 59
            total_minutes = total_minutes - 1 if modulo_seconds == 59 else total_minutes

        return f'{total_minutes:02d}:{modulo_seconds:02d}:{modulo_sectors:02d}'
    # ************************************************************************************


    # ************************************************************************************
    def _bytes_to_sectors(self, file_size: int):
        """Get the total runtime/size of a binary file in sectors, given the file size in bytes"""
        if file_size % 2352 == 0:
            return file_size // 2352
        return None
    # ************************************************************************************


    # ************************************************************************************
    def _convert_filesize_to_sectors(self, binary_file: str):
        """Get the total runtime/size of a binary file in sectors"""
        if exists(binary_file):
            return self._bytes_to_sectors(getsize(binary_file))
        self._debug_print(f'ERROR: Binary file not found: {binary_file}')
        return None
    # ************************************************************************************


    # ************************************************************************************
    def _timecode_addition(self, time_code: str, offset: str) -> str:
        """Add two timecodes together, capping at 449999 sectors"""
        time_code = self._timecode_to_sectors(time_code)
        offset = self._timecode_to_sectors(offset)
        result = min(time_code + offset, 449999)
        return self._sectors_to_timecode(result)
    # ************************************************************************************


    # ************************************************************************************
    def _get_cue_content(self, cue_path: str) -> Optional[list]:
        """Read and return the content of a CUE file"""
        try:
            with open(cue_path, 'r', encoding='utf-8') as cue_file:
                return cue_file.read().splitlines()
        except IOError:
            self._debug_print(f'ERROR: Could not open {cue_path}')
            return None
    # ************************************************************************************


    # ************************************************************************************
    def _is_cue_mode_valid(self, cue_path: str, cue_content: list) -> bool:
        """Check if the CUE file uses MODE2/2352"""
        for line in cue_content:
            if self._RE_MODE2.match(line):
                return True
        self._debug_print(f'ERROR: This cue sheet is not in MODE2/2352: {cue_path}')
        return False
    # ************************************************************************************


    # ************************************************************************************
    def _get_number_of_tracks(self, cue_content: list) -> int:
        """Count the number of tracks in the CUE sheet"""
        return sum(1 for line in cue_content if self._RE_TRACK.match(line)
                   and not self._RE_FILE_TRACK.match(line))
    # ************************************************************************************


    # ************************************************************************************
    def _write_cu2_file(self, binary_file, output: str) -> bool:
        """Write the CU2 file"""
        cu2_path = binary_file.rsplit('.', 1)[0] + '.cu2'
        try:
            with open(cu2_path, 'wb') as cu2_file:
                cu2_file.write(output.encode())
            return True
        except IOError:
            self._debug_print(f'ERROR: Could not write to: {cu2_path}')
            return False
    # ************************************************************************************


    # ************************************************************************************
    def _get_track_index(self, cue_content: list, track: int) -> tuple:
        """Find the index positions (00 and 01) for a given track"""
        track_re = compile(rf'.*track\s+0?{track}\b.*', IGNORECASE)
        for i, line in enumerate(cue_content):
            if track_re.match(line):
                index_00 = cue_content[i + 1][::-1][:8][::-1] \
                    if i + 1 < len(cue_content) and self._RE_INDEX_00.match(cue_content[i + 1]) \
                    else None
                if i + 1 < len(cue_content) and self._RE_INDEX_01.match(cue_content[i + 1]):
                    index_01 = cue_content[i + 1][::-1][:8][::-1]
                elif i + 2 < len(cue_content) and self._RE_INDEX_01.match(cue_content[i + 2]):
                    index_01 = cue_content[i + 2][::-1][:8][::-1]
                else:
                    index_01 = None
                return index_00, index_01
        return None, None
    # ************************************************************************************


    # ************************************************************************************
    def _process_pregap(self, track: int, index_00: str, index_01: str, cue_path: str) -> str:
        """Process pregap for a track and return the formatted output"""
        if index_00 and self.format_revision == 2:
            timecode_addition = self._timecode_addition(index_00, "00:02:00")
            timecode_sectors = self._timecode_to_sectors(timecode_addition)
            return f'pregap{track:02d}  {self._sectors_to_timecode_alternative(timecode_sectors)}\r\n'
        elif index_00 is None and index_01 and self.format_revision == 2:
            self._debug_print(f'WARNING: The PREGAP command is used for track {track}, which requires the software to insert data into the image or disc. '
                              f'This is not supported. Using index 01 as pregap.')
            timecode_addition = self._timecode_addition(index_01, "00:02:00")
            timecode_sectors = self._timecode_to_sectors(timecode_addition)
            return f'pregap{track:02d}  {self._sectors_to_timecode_alternative(timecode_sectors)}\r\n'
        else:
            self._debug_print(f'ERROR: Could not find pregap position (index 00) for track {track} in cue sheet: {cue_path}')
            return None
    # ************************************************************************************


    # ************************************************************************************
    def _process_track(self, track: int, index_01: str, cue_path: str) -> str:
        """Process track start position and return the formatted output"""
        if index_01:
            timecode_addition = self._timecode_addition(index_01, "00:02:00")
            timecode_sectors = self._timecode_to_sectors(timecode_addition)
            return f'track{track:02d}   {self._sectors_to_timecode_alternative(timecode_sectors)}\r\n'
        self._debug_print(f'ERROR: Could not find starting position (index 01) for track {track} in cue sheet: {cue_path}')
        return None
    # ************************************************************************************


    # ************************************************************************************
    def generate_cu2(self, cue_path: str, binary_file_name: str) -> bool:
        """Generate a CU2 file from a CUE file"""
        # Read and validate CUE file
        cue_content = self._get_cue_content(cue_path)
        if not cue_content:
            return False

        if not self._is_cue_mode_valid(cue_path, cue_content):
            return False

        # Set up paths and initialize output
        bin_path = str(Path(cue_path).parent)
        binary_file = join(bin_path, binary_file_name)
        output = []

        # Get number of tracks
        number_of_tracks = self._get_number_of_tracks(cue_content)
        output.append(f'ntracks {number_of_tracks}\r\n')

        # Get total size in sectors
        sectors = self._convert_filesize_to_sectors(binary_file)
        if sectors is None:
            return False
        output.append(f'size    {self._sectors_to_timecode(sectors)}\r\n')

        # Add data1 (hardcoded offset for track 1)
        output.append(f'data1   {self._timecode_addition("00:00:00", "00:02:00")}\r\n')

        # Process tracks 2 and above
        for track in range(2, number_of_tracks + 1):
            index_00, index_01 = self._get_track_index(cue_content, track)

            # Handle pregap
            pregap_output = self._process_pregap(track, index_00, index_01, cue_path)
            if pregap_output is None:
                return False
            output.append(pregap_output)

            # Handle track start
            track_output = self._process_track(track, index_01, cue_path)
            if track_output is None:
                return False
            output.append(track_output)

        # Add end of last track
        timecode_addition = self._timecode_addition(self._sectors_to_timecode(sectors), "00:02:00")
        timecode_sectors = self._timecode_to_sectors(timecode_addition)
        output.append(f'\r\ntrk end   {self._sectors_to_timecode_alternative(timecode_sectors)}')

        # Write CU2 file
        return self._write_cu2_file(binary_file, ''.join(output))
    # ************************************************************************************
