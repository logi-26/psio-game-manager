'''
Classes for the Game object, Cuesheet object, and Binfile object.
'''

# ************************************************************************************
class Game:
    def __init__(self, directory_name, directory_path, game_id, disc_number, disc_collection, cue_sheet, cover_art_present, cu2_present, cu2_required, multi_disc_file_present, libcrypt_required):
        self._directory_name = directory_name
        self._directory_path = directory_path
        self._id = game_id
        self._disc_number = disc_number
        self._disc_collection = disc_collection
        self._cue_sheet = cue_sheet
        self._cover_art_present = cover_art_present
        self._cu2_present = cu2_present
        self._cu2_required = cu2_required
        self._multi_disc_file_present = multi_disc_file_present
        self._libcrypt_required = libcrypt_required

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

    # Getter and setter for cue_sheet
    def get_cue_sheet(self):
        return self._cue_sheet

    def set_cue_sheet(self, value):
        self._cue_sheet = value

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
# ************************************************************************************


# ************************************************************************************
class Cuesheet:
    def __init__(self, file_name, file_path, game_name):
        self._file_name = file_name
        self._file_path = file_path
        self._game_name = game_name
        self._new_name = None
        self._bin_files = []

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

    def set_bin_files(self, value):
        self._bin_files = value

    def add_bin_file(self, bin_file):
        self._bin_files.append(bin_file)
# ************************************************************************************


# ************************************************************************************
class Binfile:
    def __init__(self, file_name, file_path):
        self._file_name = file_name
        self._file_path = file_path
        self._new_name = None

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

    # Getter and setter for new_name
    def get_new_name(self):
        return self._new_name

    def set_new_name(self, new_name):
        self._new_name = new_name
# ************************************************************************************
