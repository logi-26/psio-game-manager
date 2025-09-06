'''
Classes for the Game object, Cuesheet object, Binfile object and Tracks.
'''

from os.path import getsize, isfile


# ************************************************************************************
class Game:
    """A Game object with its associated cue sheet"""
    def __init__(self, directory_name, directory_path, game_id, disc_number, disc_collection, cue_sheet, cover_art_present, cu2_present, cu2_required, multi_disc_file_present, libcrypt_required):
        self._directory_name = directory_name
        self._directory_path = directory_path
        self._id = game_id
        self._disc_number = disc_number
        self._disc_collection = disc_collection
        self._cover_art_present = cover_art_present
        self._cu2_present = cu2_present
        self._cu2_required = cu2_required
        self._multi_disc_file_present = multi_disc_file_present
        self._libcrypt_required = libcrypt_required
        self._crc_valid = None
        self._cue_sheet: Cuesheet = cue_sheet

    # Getter and setter for directory_name
    def get_directory_name(self):
        return self._directory_name

    def set_directory_name(self, new_name):
        self._directory_name = new_name

    # Getter and setter for directory_path
    def get_directory_path(self):
        return self._directory_path

    def set_directory_path(self, value):
        self._directory_path = value

    # Getter and setter for id
    def get_id(self):
        return self._id

    def set_id(self, value):
        self._id = value

    # Getter and setter for disc_number
    def get_disc_number(self):
        return self._disc_number

    def set_disc_number(self, value):
        self._disc_number = value

    # Getter and setter for disc_collection
    def get_disc_collection(self):
        return self._disc_collection

    def set_disc_collection(self, value):
        self._disc_collection = value

    # Getter and setter for cover_art_present
    def get_cover_art_present(self):
        return self._cover_art_present

    def set_cover_art_present(self, value):
        self._cover_art_present = value

    # Getter and setter for cu2_present
    def get_cu2_present(self):
        return self._cu2_present

    def set_cu2_present(self, value):
        self._cu2_present = value

    # Getter and setter for cu2_required
    def get_cu2_required(self):
        return self._cu2_required

    def set_cu2_required(self, value):
        self._cu2_required = value

    # Getter and setter for multi_disc_file_present
    def get_multi_disc_file_present(self):
        return self._multi_disc_file_present

    def set_multi_disc_file_present(self, value):
        self._multi_disc_file_present = value

    # Getter and setter for libcrypt_required
    def get_libcrypt_required(self):
        return self._libcrypt_required

    def set_libcrypt_required(self, value):
        self._libcrypt_required = value

    # Getter and setter for cue_sheet
    def get_cue_sheet(self):
        return self._cue_sheet

    def set_cue_sheet(self, value):
        self._cue_sheet = value

    # Getter and setter for crc_valid
    def get_crc_valid(self):
        return self._crc_valid

    def set_crc_valid(self, value):
        self._crc_valid = value
# ************************************************************************************


# ************************************************************************************
class Cuesheet:
    """A cue sheet with its associated binary files"""
    def __init__(self, file_name, file_path, game_name):
        self._file_name = file_name
        self._file_path = file_path
        self._game_name = game_name
        self._new_name = None
        self._bin_files: Binfile = []

    # Getter and setter for file_name
    def get_file_name(self):
        return self._file_name

    def set_file_name(self, value):
        self._file_name = value

    # Getter and setter for file_path
    def get_file_path(self):
        return self._file_path

    def set_file_path(self, value):
        self._file_path = value

    # Getter and setter for game_name
    def get_game_name(self):
        return self._game_name

    def set_game_name(self, value):
        self._game_name = value

    # Getter and setter for new_name
    def get_new_name(self):
        return self._new_name

    def set_new_name(self, new_name):
        self._new_name = new_name

    # Getter and setter for bin_files
    def get_bin_files(self):
        return self._bin_files

    def set_bin_files(self, bin_files):
        self._bin_files = bin_files

    def add_bin_file(self, bin_file):
        self._bin_files.append(bin_file)
# ************************************************************************************


# ************************************************************************************
class Binfile:
    """A binary file with its associated tracks"""
    def __init__(self, file_name, file_path):
        self._file_name = file_name
        self._file_path = file_path
        self._new_name = None
        self._size = getsize(file_path) if isfile(file_path) else 0
        self._tracks: Track = []

    # Getter and setter for the file_name
    def get_file_name(self):
        return self._file_name

    def set_file_name(self, value):
        self._file_name = value

    # Getter and setter for the file_path
    def get_file_path(self):
        return self._file_path

    def set_file_path(self, value):
        self._file_path = value
        self._size = getsize(value) if isfile(value) else 0

    # Getter and setter for the new_name
    def get_new_name(self):
        return self._new_name

    def set_new_name(self, value):
        self._new_name = value

    # Getter and setter for the tracks
    def get_tracks(self):
        return self._tracks

    def set_tracks(self, value):
        self._tracks = value

    def add_track(self, track):
        self._tracks.append(track)

    # Getter and setter for the size
    def get_size(self):
        return self._size

    def set_size(self, value):
        self._size = value
# ************************************************************************************


# ************************************************************************************
class Track:
    """A track within a binary file"""
    globalBlocksize = None

    def __init__(self, track_number, track_type, pregap=None, sectors=None, size=None, crc32=None):
        self._track_number = track_number
        self._track_type = track_type
        self._indexes = []
        self._pregap = pregap
        self._sectors = sectors
        self._size = size
        self._crc32 = crc32
        self._file_offset = None
        self._block_size = None

        # Set block size based on track_type if not already set
        if not self._block_size:
            if track_type in ['AUDIO', 'MODE1/2352', 'MODE2/2352', 'CDI/2352']:
                self._block_size = 2352
            elif track_type == 'CDG':
                self._block_size = 2448
            elif track_type == 'MODE1/2048':
                self._block_size = 2048
            elif track_type in ['MODE2/2336', 'CDI/2336']:
                self._block_size = 2336

    # Getter and setter for track_number
    def get_track_number(self):
        return self._track_number

    def set_track_number(self, value):
        self._track_number = value

    # Getter and setter for track_type
    def get_track_type(self):
        return self._track_type

    def set_track_type(self, value):
        self._track_type = value

    # Getter and setter for indexes
    def get_indexes(self):
        return self._indexes

    def set_indexes(self, value):
        self._indexes = value

    def add_index(self, index):
        self._indexes.append(index)

    # Getter and setter for pregap
    def get_pregap(self):
        return self._pregap

    def set_pregap(self, value):
        self._pregap = value

    # Getter and setter for the sectors
    def get_sectors(self):
        return self._sectors

    def set_sectors(self, value):
        self._sectors = value

    # Getter and setter for the size
    def get_size(self):
        return self._size

    def set_size(self, value):
        self._size = value

    # Getter and setter for the crc32
    def get_crc32(self):
        return self._crc32

    def set_crc32(self, value):
        self._crc32 = value

    # Getter and setter for the offset
    def get_file_offset(self):
        return self._file_offset

    def set_file_offset(self, value):
        self._file_offset = value

    # Getter and setter for the block_size
    def get_block_size(self):
        return self._block_size

    def set_block_size(self, value):
        self._block_size = value
# ************************************************************************************
