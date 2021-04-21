#!/usr/bin/env python3
#
#  psio-assist
#
#  This is basically a GUI and wrapper for the binmerge and cue2cu2 scripts
#  This has a very basic UI for selecting a directory that contains bin/cue files
#  The script will check if the bin files need to be merged, create the cu2 file and add the game cover
#
#  Copyright (C) 2021 LoGi26
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from tkinter import *
from tkinter import ttk, filedialog
from tkinter.ttk import Progressbar
from pathlib import Path
from os.path import exists, join, abspath, basename, dirname, splitext
from sys import argv, exit
from os import mkdir, walk, listdir
from shutil import copyfile
from time import sleep

# Local imports
from binmerge import start_bin_merge, read_cue_file, set_binmerge_error_log_path
from cue2cu2 import start_cue2cu2, set_cu2_error_log_path

# Get the directory paths based on the scripts location
script_root_dir = Path(abspath(dirname(argv[0])))
output_path = join(dirname(script_root_dir), 'output')
log_path = join(dirname(script_root_dir), 'error_log')
covers_path = join(dirname(script_root_dir), 'covers')
error_log_file = join(log_path, 'log.txt')

# Set the error log path for all of the scripts
set_cu2_error_log_path(error_log_file)
set_binmerge_error_log_path(error_log_file)

game_data = []
window = None
CURRENT_REVISION = 0.1


# *****************************************************************************************************************
# Function that processes a single game
def _process_single_game(cue_path):
	label_progress.configure(text = 'Reading original bin files...')

	# Get the game name (using data from redump rather than the cue sheet so that multi-disc games go into 1 folder)
	game_name = _get_game_name(cue_path)
	original_game_name = _get_game_name_from_cue(cue_path, False)
	game_id = _get_game_id(join(dirname(cue_path) , f'{_get_game_name_from_cue(cue_path, True)}.bin'))
	
	# If we do not have info for this game we will use the game name from the original cue file
	if game_name == '':
		game_name = original_game_name.replace('.', '-')
	
	if game_name != '':
		label_progress.configure(text = 'Creating game directory...')
		_update_progress_bar(15)
	 
		# Create the game output directory and ensure multi-disc games go into the same directory
		game_dir_name = game_name
		if len(game_name) > 9:
			if game_name[len(game_name)-7:-3] == 'Disc':
				game_dir_name = game_name[:-9]	
		game_output_path = join(output_path, game_dir_name)

		if _create_directory(game_output_path):
			out_bin_path = join(game_output_path, f'{game_name}.bin')
			out_cue_path = join(game_output_path, f'{game_name}.cue')
			out_cu2_path = join(game_output_path, f'{game_name}.cu2')
			
			if not exists(out_bin_path) and not exists(out_cu2_path):
				label_progress.configure(text = 'Checking original files...')
				
				# Ensure that all of the required files exist
				if _all_game_files_exist(cue_path):
					_update_progress_bar(30)
				
					# If the game is a multi-bin game, merge the bin files using the binmerge script, otherwise copy the single bin file
					if _is_multi_bin(cue_path):
						label_progress.configure(text = 'Merging BIN files...')
						start_bin_merge(cue_path, game_name, game_output_path)
					else:
						label_progress.configure(text = 'Copying BIN file...')
						copyfile(join(dirname(cue_path) , f'{original_game_name}.bin'), out_bin_path)
						
						label_progress.configure(text = 'Copying CUE file...')
						copyfile(cue_path, out_cue_path)
					
					_update_progress_bar(60)
					
					# Generate the CU2 file using the cue2cu2 script
					label_progress.configure(text = 'Generating CU2 file...')
					start_cue2cu2(out_cue_path, f'{game_name}.bin')
						
					_update_progress_bar(90)
						
					# Copy the game cover (if it exists) to the games output directory
					_copy_game_cover(game_output_path, covers_path, game_id, game_dir_name)
					
					if exists(out_bin_path) and exists(out_cu2_path):
						label_progress.configure(text = 'Finished processing game...')
					else:
						label_progress.configure(text = 'Error processing game...') 
				else:
					_log_error('ERROR', f'NOT all game files exists: {cue_path}')
			else:
				_log_error('ERROR', f'Game output directory already exists: {game_name}')
				label_progress.configure(text = f'Game already exists: {game_name}')
		else:
			_log_error('ERROR', f'Unable to create the game output directory: {game_output_path}')
	else:
		_log_error('ERROR', f'Could not determine the game name: {cue_path}')
						
	_update_progress_bar(100)
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that processes multiple games in batch mode
def _process_multiple_games(selected_path):
	cue_list = []
	for root, dirs, files in walk(selected_path):
		for file in files:
			if file.lower().endswith('.cue'):
				 cue_list.append(join(root, file))
	
	for cue_file in cue_list:
		_process_single_game(cue_file)
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that reads the game data file into a list
def _read_game_data_file():
	game_data_file = join(script_root_dir, 'game_data')
	lines = []
	with open(game_data_file) as f:
		lines = f.readlines()
	lines = [x.strip() for x in lines] 
	for line in lines:
		split_line = line.split(',')
		try:
			game_data.append((split_line[0], split_line[1].strip(), int(split_line[2].strip())))
		except:
			pass
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that gets the disc number (using data from redump)
def _get_disc_number(game_id):
	for line in game_data:
		if line[0] == game_id:
			return line[2]
	return 0
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to get the game name (using names from redump and the psx data-centre)
def _get_game_name(cue_path):
	game_id = _get_game_id(join(dirname(cue_path) , f'{_get_game_name_from_cue(cue_path, True)}.bin'))
	for line in game_data:
		if line[0] == game_id:
			game_name = line[1]
			
			# Ensure that the game name (including disc number and extension) is not more than 60 chars
			if int(line[2]) > 0:
				if len(game_name) <= 47:
					return f'{game_name} (Disc {line[2]})'
				else:
					return f'{game_name[:47]} (Disc {line[2]})'
			else:
				if len(game_name) <= 47:
					return line[1]
				else:
					return f'{line[1][:47]}'
	return ''
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to get the game name from the cue sheet (using the binmerge script)
def _get_game_name_from_cue(cue_path, include_track):
	cue_content = read_cue_file(cue_path)
	if cue_content != []:
		game_name = basename(cue_content[0].filename)
		if not include_track:
			if 'Track' in game_name:
				game_name = game_name[:game_name.rfind('(', 0) -1]
		return splitext(game_name)[0]
	return ''
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that generates a MULTIDISC.LST file for multi-disc games
def _generate_multidisc_file():
	game_directories = listdir(output_path)
	for game_dir in game_directories:
		bin_files = [f for f in listdir(join(output_path, game_dir)) if f.endswith('.bin')]

		# If there is more than 1 bin file, this should be a multi-disc game
		multi_disc_bins = []
		if len(bin_files) > 1:
			for bin_file in bin_files:
				disc_number = _get_disc_number(_get_game_id(join(output_path, game_dir, bin_file)))
				if disc_number > 0:
					multi_disc_bins.insert(disc_number-1, bin_file)

		# Create the MULTIDISC.LST file
		if len(multi_disc_bins) > 0:
			with open(join(output_path, game_dir, 'MULTIDISC.LST'), 'w') as multi_disc_file:
				for count, binfile in enumerate(multi_disc_bins):
					if count < len(multi_disc_bins)-1:
						#multi_disc_file.write(f'{binfile}\n')
						multi_disc_file.write(f'{binfile}\r')
					else:
						multi_disc_file.write(binfile)
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to get the unique game id from the bin file
def _get_game_id(bin_file_path):
	region_codes = ['DTLS_', 'SCES_', 'SLES_', 'SLED_', 'SCED_', 'SCUS_', 'SLUS_', 'SLPS_', 'SCAJ_', 'SLKA_', 'SLPM_', 'SCPS_', 'SCPM_', 'PCPX_', 'PAPX_', 'PTPX_', 'LSP0_', 'LSP1_', 'LSP2_', 'LSP9_', 'SIPS_', 'ESPM_', 'SCZS_', 'SPUS_', 'PBPX_', 'LSP_']
	game_id = None
	if exists(bin_file_path):
		with open(bin_file_path, 'rb') as bin_file:
			while game_id == None:
				try:
					line = str(next(bin_file))
					if line != None:
						for region_code in region_codes:
							if region_code in line:
								start = line.find(region_code)
								game_id = line[start:start + 11]
				except StopIteration:
					break				 
	return game_id.replace('_', '-').replace('.', '').strip() if game_id is not None else None
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to copy the game front cover if it is available
def _copy_game_cover(output_path, covers_path, game_id, game_name):
	if exists(join(covers_path, f'{game_id}.bmp')):
		label_progress.configure(text = 'Copying game cover image...')
		copyfile(join(covers_path, f'{game_id}.bmp'), join(output_path, f'{game_name}.bmp'))
	elif exists(join(covers_path, f'{game_id}.BMP')):
		label_progress.configure(text = 'Copying game cover image...')
		copyfile(join(covers_path, f'{game_id}.BMP'), join(output_path, f'{game_name}.BMP'))  
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to check if the game is a multi-bin game
def _is_multi_bin(cue_path):
	return len(read_cue_file(cue_path)) > 1
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to check if all of the required bin files exist
def _all_game_files_exist(cue_path):
	for file in read_cue_file(cue_path):
		if not exists(file.filename):
			return False
	return True
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to create a directory
def _create_directory(dir):
	if not exists(dir):
		try:
			mkdir(dir)
		except:
			pass
	return exists(dir)
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that creates the nessasary directories for these scripts (in case the user has deleted them)
def _create_psio_assist_directories():
	output_path_exists = _create_directory(output_path)
	log_path_exists = _create_directory(log_path)
	covers_path_exists = _create_directory(covers_path)
	return output_path_exists and log_path_exists and covers_path_exists
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to log basic error messages to a file
def _log_error(error_type, error_message):
	with open(error_log_file, 'a') as error_log:
		error_log.write(f'[{error_type}]: {error_message}\n')
# *****************************************************************************************************************


# ****************************************************************
# GUI Functions
# ****************************************************************

# *****************************************************************************************************************
# This function is a hack to hide the hidden files/directories in the file browser dialog
def _prevent_hidden_files(window):
	try:
		# This will throw a TclError, so we need to catch it (It will initialise the window without displaying it)
		try:
			window.tk.call('tk_getOpenFile', '-foobarbaz')
		except TclError:
			pass
		window.tk.call('set', '::tk::dialog::file::showHiddenBtn', '1')
		window.tk.call('set', '::tk::dialog::file::showHiddenVar', '0')
	except:
		pass
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function to update the progress bar
def _update_progress_bar(value):
	progress_bar['value'] = value
	if window is not None:
		window.update()
	sleep(0.1)
# *****************************************************************************************************************


# *****************************************************************************************************************
# Browse button click event 
def _browse_button_clicked():
	user_selected_path.set(filedialog.askdirectory(initialdir = '/', title = 'Select Game Directory'))
	
	# Update the label
	label_input.configure(text = user_selected_path.get())
	
	if user_selected_path.get() is not None and user_selected_path.get() != '':
		button_start['state'] = 'normal'
# *****************************************************************************************************************


# *****************************************************************************************************************
# Start button click event 
def _start_button_clicked():
	if not user_selected_path.get() == '':
		button_start['state'] = 'disabled'
		
		# Start the process
		_process_multiple_games(user_selected_path.get())
		_generate_multidisc_file()

		# Wait for 2 seconds and then reset the progress bar
		sleep(2)
		_update_progress_bar(0)
		label_progress.configure(text = 'Progress...')

		button_start['state'] = 'normal'
# *****************************************************************************************************************


# ****************************************************************
# Script Start
# ****************************************************************
if not _create_psio_assist_directories():
	_log_error('ERROR', 'Unable to create some of the required directories.')
	exit()
	
_read_game_data_file()
if len(game_data) == 0:
	_log_error('ERROR', 'Unable to read the \'game_data\' file.')
	exit()
	
# ****************************************************************
# GUI Code Start
# ****************************************************************
# Create the window
window = Tk() 
  
# App title
window.title(f'PSIO Game Assistant  v{CURRENT_REVISION}') 
  
# The GUI window size
window.geometry('600x150') 

# Set window background color
window.config(background = '#c9c9c7')

# Radio button to select single game or batch mode
controls_y = 0.02

# Label to display the selected path
user_selected_path = StringVar()
label_input = Label(window, text = user_selected_path.get(), width = 60, height = 4, bg = 'white', fg = 'black', borderwidth=2, relief='solid')
label_input.place(relx=0.01, rely=controls_y + 0.10, relwidth=0.79, relheight=0.22)

# Button to browse the filesystem and select the path
button_browse = Button(window, text = 'Browse', command = _browse_button_clicked)
button_browse.place(relx=0.81, rely=controls_y + 0.10, relwidth=0.18, relheight=0.22)

# Button to start the process
button_start = Button(window, text = 'Start', command = _start_button_clicked)
button_start.place(relx=0.01, rely=controls_y + 0.45, relwidth=0.19, relheight=0.22)
button_start['state'] = 'disabled'

# Progressbar to inform the user of the progress
progress_bar = Progressbar(window, orient = HORIZONTAL, length = 100, mode = 'determinate')
progress_bar.place(relx=0.21, rely=controls_y + 0.45, relwidth=0.78, relheight=0.22)

# Label to display the progress info
label_progress = Label(window, text = 'Progress...', width = 60, height = 4, bg = '#c9c9c7', fg = 'black', highlightthickness=0, anchor='e')
label_progress.place(relx=0.21, rely=controls_y + 0.7, relwidth=0.78, relheight=0.2)

_prevent_hidden_files(window)

# Loop to display/control the GUI
window.mainloop() 
# ****************************************************************
# GUI Code End
# ****************************************************************
