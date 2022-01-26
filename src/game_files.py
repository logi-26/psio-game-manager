
# *****************************************************************************************************************
class Game:
	def __init__(self, directory_name, directory_path, game_id, disc_number, disc_collection, cue_sheet, cover_art_present, cu2_present):
		self.directory_name = directory_name
		self.directory_path = directory_path
		self.id = game_id
		self.disc_number = disc_number
		self.disc_collection = disc_collection
		self.cue_sheet = cue_sheet
		self.cover_art_present = cover_art_present
		self.cu2_present = cu2_present
		
	def set_new_directory_name(self, new_name):
		self.directory_name = new_name
# *****************************************************************************************************************


# *****************************************************************************************************************
class Cuesheet:
	def __init__(self, file_name, file_path, game_name):
		self.file_name = file_name
		self.file_path = file_path
		self.game_name = game_name
		self.new_name = None
		self.bin_files = []
		
	def add_bin_file(self, bin_file):
		self.bin_files.append(bin_file)
		
	def set_new_name(self, new_name):
		self.new_name = new_name
# *****************************************************************************************************************


# *****************************************************************************************************************
class Binfile:
	def __init__(self, file_name, file_path):
		self.file_name = file_name
		self.file_path = file_path
		self.new_name = None

	def set_new_name(self, new_name):
		self.new_name = new_name
# *****************************************************************************************************************
