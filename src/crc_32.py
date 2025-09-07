'''
Performs CRC-32 checks on each of the Tracks in the BIN file/s
'''

# System imports
from os.path import exists, getsize
from zlib import crc32

# Local imports
from game_files import Cuesheet


class CrcFileVerifier:
    def __init__(self, debug_mode: bool = False):
        """Class to verify the Tracks in a BIN file"""
        self.debug_mode = debug_mode

        # Standard sector size for PlayStation Mode 2 and audio tracks
        self.sector_size = 2352


    # ************************************************************************************
    def _debug_print(self, message: str):
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(message)
    # ************************************************************************************


    # ************************************************************************************
    def compute_start_sectors(self, redump_tracks: list, include_pregap: bool = True) -> list:
        """Compute start sectors for tracks, optionally including pregaps"""
        start_sectors = []
        curr_sector = 0

        # Loop through the Redump tracks
        for track in redump_tracks:

            # Calculate the start sector
            start_sectors.append(curr_sector)
            sectors = int(track['sectors']) if track['sectors'] is not None else 0
            pregap = int(track['pregap']) if track['pregap'] is not None else 0
            curr_sector += sectors + (pregap if include_pregap else 0)

        # Return the list of start sectors for the tracks
        return start_sectors
    # ************************************************************************************


    # ************************************************************************************
    def calculate_crc32(self, file_path: str, start_byte: int = 0, max_bytes=None) -> str:
        """Calculate CRC-32 for a file segment"""
        crc32_hash = 0

        # Open the BIN file
        with open(file_path, 'rb') as f:

            # Seek to the start byte
            f.seek(start_byte)
            bytes_read = 0

            # Read the chunk and perform CRC hash
            while chunk := f.read(8192):
                if max_bytes is not None and bytes_read + len(chunk) > max_bytes:
                    chunk = chunk[:max_bytes - bytes_read]
                crc32_hash = crc32(chunk, crc32_hash)
                bytes_read += len(chunk)
                if max_bytes is not None and bytes_read >= max_bytes:
                    break

        # Return the CRC hash
        return format(crc32_hash & 0xFFFFFFFF, '08X').lower()
    # ************************************************************************************


    # ************************************************************************************
    def _parse_cue_tracks(self, cuesheet: Cuesheet, start_sectors=None) -> list:
        """Extract track information and BIN file paths from a populated Cuesheet object"""
        tracks = []

        # Track counter for start_sectors indexing
        track_index = 0

        # Loop through the associated BIN files
        for bin_file in cuesheet.get_bin_files():
            bin_file_path = bin_file.get_file_path()

            # Loop through the tracks in the BIN file
            for track in bin_file.get_tracks():
                # Extract track-specific data
                track_info = {
                    'file': bin_file_path,
                    'track_number': track.get_track_number() if hasattr(track, 'get_track_number') else track_index + 1,
                    'start_sector': start_sectors[track_index] if start_sectors is not None and track_index < len(start_sectors) else 0
                }
                tracks.append(track_info)
                track_index += 1

        # Return the list of tracks
        return tracks
    # ************************************************************************************


    # ************************************************************************************
    def verify_tracks(self, cuesheet: Cuesheet, redump_tracks: list) -> bool:
        """Verify CRC-32 for tracks"""
        if not exists(cuesheet.get_file_path()):
            print(f"(Error) CUE file '{cuesheet.get_file_path()}' does not exist!")
            return False

        self._debug_print("\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        self._debug_print("Performing CRC-32 checks...")

        # Parse tracks using the CUE file
        cue_tracks = self._parse_cue_tracks(cuesheet)

        # Print a warning and return if the number of tracks do not match
        if len(cue_tracks) != len(redump_tracks):
            print(f"\n(Warning) CUE file has {len(cue_tracks)} tracks, "
                f"but database expects {len(redump_tracks)} tracks!")
            print(f"game name: {cuesheet.get_game_name()}\n")
            return False

        # Detect if it is a single BIN or multiple BIN files
        bin_files = list(set(track['file'] for track in cue_tracks if track['file']))
        single_bin = len(bin_files) == 1

        if single_bin:
            # Compute start sectors for each track, excluding pregaps for merged BIN
            start_sectors = self.compute_start_sectors(redump_tracks, include_pregap=False)
            for i, cue_track in enumerate(cue_tracks):
                cue_track['start_sector'] = start_sectors[i]

        # Print debug info
        if single_bin:
            if len(redump_tracks) > 1:
                self._debug_print("\nDetected: Single BIN file")
                self._debug_print(f"Contains multiple tracks ({len(redump_tracks)}) - the BIN was likely merged\n")
        else:
            self._debug_print(f"\nDetected: Multiple BIN file ({len(bin_files)})\n")

        all_tracks_passed = True

        # Loop through the tracks
        for index, (cue_track, redump_track) in enumerate(zip(cue_tracks, redump_tracks), 1):
            track_num = redump_track["track"]
            expected_crc32 = redump_track["crc32"]
            expected_size = int(redump_track["size"])
            expected_sectors = int(redump_track["sectors"])

            bin_file = cue_track['file']
            if not bin_file or not exists(bin_file):
                print(f"\n(Warning) Track {track_num} - Missing BIN file '{bin_file}'!")
                return False

            if single_bin:
                start_sector = cue_track.get('start_sector', 0)
                start_byte = start_sector * self.sector_size
                track_size_bytes = expected_sectors * self.sector_size

                # Verify track size
                if track_size_bytes != expected_size:
                    print(f"\n(Warning) Track {track_num} - Calculated size "
                        f"({track_size_bytes} bytes) does not match database "
                        f"({expected_size} bytes)")
                    all_tracks_passed = False
                    print(f"game name: {cuesheet.get_game_name()}\n")
                    continue

                # Perform the CRC-32 calculation on the BIN file
                crc32_result = self.calculate_crc32(bin_file, start_byte=start_byte, max_bytes=track_size_bytes)

            else:
                # Multiple BIN - Use entire BIN file
                file_size = getsize(bin_file)
                if file_size != expected_size:
                    print(f"\n(Warning) Track {track_num} - Calculated size "
                        f"({file_size} bytes) does not match database "
                        f"({expected_size} bytes)")
                    print(f"game name: {cuesheet.get_game_name()}\n")
                    all_tracks_passed = False
                    continue

                # Perform the CRC-32 calculation on the BIN file
                crc32_result = self.calculate_crc32(bin_file, max_bytes=expected_size)

            # Compare CRC-32
            if crc32_result == expected_crc32:
                self._debug_print(f"Track {track_num}: CRC-32 matches database!")
            else:
                self._debug_print(f"Track {track_num}: CRC-32 does not match database (expected {expected_crc32}).")
                all_tracks_passed = False

            # Verify start sector (for single BIN)
            if single_bin:
                expected_start_sector = sum(
                    int(track["sectors"]) for track in redump_tracks[:index-1]
                )  # Exclude pregaps for merged BIN

                if cue_track['start_sector'] != expected_start_sector:
                    print(f"\n(Warning) Track {track_num} - CUE start sector "
                        f"({cue_track['start_sector']}) does not match database "
                        f"({expected_start_sector})")
                    print(f"game name: {cuesheet.get_game_name()}\n")
                    all_tracks_passed = False

        self._debug_print(f"\nAll Tracks Passed CRC checks: {all_tracks_passed}")
        self._debug_print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        return all_tracks_passed
    # ************************************************************************************
