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
    def calculate_crc32(self, file_path: str, start_byte: int = 0, max_bytes=None):
        """Calculate CRC-32 for a file segment"""
        crc32_hash = 0
        with open(file_path, 'rb') as f:
            f.seek(start_byte)
            bytes_read = 0
            while chunk := f.read(8192):
                if max_bytes is not None and bytes_read + len(chunk) > max_bytes:
                    chunk = chunk[:max_bytes - bytes_read]
                crc32_hash = crc32(chunk, crc32_hash)
                bytes_read += len(chunk)
                if max_bytes is not None and bytes_read >= max_bytes:
                    break
        return format(crc32_hash & 0xFFFFFFFF, '08X').lower()
    # ************************************************************************************


    # ************************************************************************************
    def _parse_cue_tracks(self, cuesheet: Cuesheet) -> list:
        """Extract track information and BIN file paths from a populated Cuesheet object"""
        tracks = []
        for bin_file in cuesheet.get_bin_files():
            bin_file_path = bin_file.get_file_path()
            for track in bin_file.get_tracks():
                track_info = {
                    'file': bin_file_path,
                    'start_sector': track.get_sectors() if track.get_sectors() is not None else 0
                }
                tracks.append(track_info)
        return tracks
    # ************************************************************************************


    # ************************************************************************************
    def verify_tracks(self, cuesheet: Cuesheet, redump_tracks: list) -> bool:
        """Verify CRC-32 for tracks"""
        if not exists(cuesheet.get_file_path()):
            print(f"(Error) CUE file '{cuesheet.get_file_path()}' does not exist!")
            return False

        self._debug_print("\nPerforming CRC-32 checks...")

        # Parse CUE file
        cue_tracks = self._parse_cue_tracks(cuesheet)

        if len(cue_tracks) != len(redump_tracks):
            print(f"\n(Warning) CUE file has {len(cue_tracks)} tracks, "
                f"but database expects {len(redump_tracks)} tracks!")
            print(f"game name: {cuesheet.get_game_name()}\n")
            return False

        # Detect single BIN or multiple BIN files
        bin_files = list(set(track['file'] for track in cue_tracks if track['file']))
        single_bin = len(bin_files) == 1

        self._debug_print(f"Detected: {'Single BIN file' if single_bin else 'Multiple BIN files'} "
                 f"({len(bin_files)} BIN file(s))\n")

        all_tracks_passed = True

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
                # Single BIN - Use start_sector from CUE and database sector count
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
            if single_bin and 'start_sector' in cue_track:

                expected_start_sector = sum(
                    (int(track["sectors"]) if track["sectors"] is not None else 0) +
                    (int(track["pregap"]) if track["pregap"] is not None else 0)
                    for track in redump_tracks[:index-1]
                )

                if cue_track['start_sector'] != expected_start_sector:
                    print(f"\n(Warning) Track {track_num} - CUE start sector "
                        f"({cue_track['start_sector']}) does not match database "
                        f"({expected_start_sector})")
                    print(f"game name: {cuesheet.get_game_name()}\n")
                    all_tracks_passed = False

        return all_tracks_passed
    # ************************************************************************************
