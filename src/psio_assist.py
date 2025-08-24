#!/usr/bin/env python3
#
#  psio-assist
#
#  This is an open-source application for preparing PlayStation games for use with a PSIO device
#
#  Features:
#  * Runs in batch mode, processing all of the games that have been selected
#  * Mmerge any games that have multiple bin files into a single bin file
#  * Update the cue sheet file to only contain a single bin file
#  * Detect games that use CCDA audio and generate a cu2 file
#  * Fix any game names that are too long or contain invalid characters
#  * Add a bmp image file for each game in the correct resolution for the PSIO menu
#  * Detect multi-disc games and organise them into a single directory and generate a multi-disc lst file
#
#  Optional:
#  Rename all games using the game names from the PlayStation Redump project
#
#  Usage:
#  Place your PlayStation games into sub-directories that each contains the bin/cue files for the game
#  Point the application at the folder root directory and it will detect the games in the sub-directories
#
#  For best performance, process your games on a computers HDD/SSD and then transfer to SD afterwards
#  Read/write speeds to and SD card are a lot slower and it can take a long time if you have lots of multi-bin games
#
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
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# System imports
from sys import argv
from os import listdir, scandir, mkdir, makedirs, remove
from os.path import exists, join, dirname, basename, splitext, abspath, isfile
from time import sleep
from json import load, dumps
from typing import Union
from re import search, sub, IGNORECASE
from pathlib2 import Path
from shutil import copyfile, move, rmtree
from PIL import Image, ImageTk
from tkinter import Menu, filedialog, StringVar, BooleanVar, TclError
from ttkbootstrap import Window, Floodgauge, Treeview, Style, Scrollbar, Labelframe, Label, Button, Checkbutton, NO, CENTER, VERTICAL
from ttkbootstrap.dialogs import MessageDialog
from ttkbootstrap.constants import DISABLED

# Local imports
from game_files import Game, Cuesheet, Binfile
from binmerge import set_binmerge_error_log_path, start_bin_merge, read_cue_file
from cue2cu2 import set_cu2_error_log_path, start_cue2cu2
from db import ensure_database_exists, select, extract_game_cover_blob

DEBUG_MODE = True

def debug_print(the_string: str):
    if DEBUG_MODE:
        print(the_string)

class PSIOGameAssistant:
    REGION_CODES = ['DTLS_', 'SCES_', 'SLES_', 'SLED_', 'SCED_', 'SCUS_', 'SLUS_', 'SLPS_', 'SCAJ_', 'SLKA_', 
                   'SLPM_', 'SCPS_', 'SCPM_', 'PCPX_', 'PAPX_', 'PTPX_', 'LSP0_', 'LSP1_', 'LSP2_', 'LSP9_', 
                   'SIPS_', 'ESPM_', 'SCZS_', 'SPUS_', 'PBPX_', 'LSP_']
    CURRENT_REVISION = 0.3
    PROGRESS_STATUS = 'Status:'
    MAX_GAME_NAME_LENGTH = 56
    INVALID_FILENAME_CHARS = r'[.\\/:*?"<>|]'
    MAX_REDUMP_NAME_LENGTH = 47
    MAX_LINES_TO_CHECK = 300
    GAME_ID_LENGTH = 11
    
    def __init__(self):

        debug_print(f'\nPSIO Game Assistant v{self.CURRENT_REVISION}')

        self.game_list = []
        self.script_root_dir = Path(abspath(dirname(argv[0])))
        self.covers_path = join(dirname(self.script_root_dir), 'covers')
        self.error_log_file = join(dirname(self.script_root_dir), 'errors.txt')
        self.CONFIG_FILE_PATH = join(self.script_root_dir, 'config')
        
        # Set error log paths
        set_cu2_error_log_path(self.error_log_file)
        set_binmerge_error_log_path(self.error_log_file)
        
        # Initialise GUI variables
        self.window = None
        self.src_path = None
        self.dest_path = None
        self.redump_rename = None
        
        # GUI elements
        self.label_progress = None
        self.progress_bar = None
        self.progress_bar_indeterminate = None
        self.button_src_scan = None
        self.button_start = None
        self.treeview_game_list = None
        self.label_src = None
        self.cover_art_frame = None


    # *****************************************************************************************************************
    def process_games(self):
        """Process the games in the game list"""

        debug_print('\nPROCESSING GAMES...')

        redump_rename = self.redump_rename.get()

        for game in self.game_list:
            game_id = game.id
            game_name = game.cue_sheet.game_name
            game_full_path = join(game.directory_path, game.directory_name)
            cue_full_path = join(game_full_path, game.cue_sheet.file_name)

            self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Processing - {game_name}')

            debug_print('\n***********************************************************')
            debug_print(f'GAME_ID: {game_id}')
            debug_print(f'GAME_NAME: {game_name}')

            if len(game.cue_sheet.bin_files) > 1:
                debug_print('MERGING BIN FILES...')
                self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Merging bin files - {game_name}')
                self._merge_bin_files(game)

                bin_path = cue_full_path[:-4] + ".bin"
                if exists(bin_path):
                    game.cue_sheet.bin_files = []
                    bin_file = Binfile(f"{game_name}.bin", bin_path)
                    game.cue_sheet.add_bin_file(bin_file)

            if game.cu2_required and not game.cu2_present:
                debug_print('GENERATING CU2...')
                self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Generating cu2 file - {game_name}')
                start_cue2cu2(cue_full_path, f'{game_name}.bin')

                cu2_path = cue_full_path[:-4] + ".cu2"
                if exists(cu2_path):
                    game.cu2_present = True

            if redump_rename:
                debug_print('RENAMING THE GAME FILES USING REDUMP...')
                self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Renaming - {game_name}')
                redump_game_name = self._game_name_validator(self._get_redump_name(game_id))
                debug_print(f'Redump Game Name: {redump_game_name}')
                self._rename_game(game, redump_game_name)
                game_name = redump_game_name

            if len(game_name) > self.MAX_GAME_NAME_LENGTH or '.' in game_name:
                debug_print('FIXING THE GAME NAME...')
                self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Validating name - {game_name}')
                new_game_name = self._game_name_validator(game)
                debug_print(f'Fixed Game Name: {new_game_name}')
                if new_game_name != game_name:
                    self._rename_game(game, new_game_name)

            if not game.cover_art_present:
                debug_print('ADDING THE GAME COVER ART...')
                self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Adding cover art - {game_name}')
                game_full_path = join(game.directory_path, game.directory_name)
                self._copy_game_cover(game_full_path, game_id, game_name)

                # If the game cover has been copied, update the game object cover details
                if exists(join(game_full_path, f'{game_name}.bmp')):
                    game.cover_art_present = True

            debug_print('***********************************************************\n')

        # Generate multi-disc games after all of the other processes have been completed
        self._generate_multidisc_files()

        self.label_progress.configure(text=self.PROGRESS_STATUS)

        # Update the game list in the GUI
        self._display_game_list()
    # *****************************************************************************************************************
        

    # *****************************************************************************************************************
    def _generate_multidisc_files(self):
        """Generate MULTIDISC.LST file for all multi-disc games"""

        debug_print('\nGENERATING MULTI-DISC FILES...\n')

        for game in self.game_list:
            
            # Find the first disc in a collection that has no multi-disc configured
            if game.disc_number == 1 and not game.multi_disc_file_present:
                
                # Get each game from the collection
                multi_games = []
                for id in game.disc_collection:
                    the_game = self._find_game_by_id(id.replace("_", "-"))
                    multi_games.append(the_game)

                if len(multi_games) > 1:
                    # Create the multi-disc folder to hold the game collection
                    multi_game_folder = self._remove_disc_from_game_name(multi_games[0].cue_sheet.game_name)
                    multi_game_path = join(multi_games[0].directory_path, multi_game_folder)
                    makedirs(multi_game_path, exist_ok=True)

                    # Process each game in the collection
                    for multi_disc in multi_games:
                        game_path = join(multi_disc.directory_path, multi_disc.directory_name)

                        # Move all of the files for the disc into the multi-disc directory
                        for filename in listdir(game_path):
                            source_path = join(game_path, filename)
                            target_path = join(multi_game_path, filename)
                            filename_no_extension = splitext(filename)[0]

                            if isfile(source_path):
                                try:
                                    move(source_path, target_path)
                                except Exception as e:
                                    print(f"Error moving {filename}: {e}")

                        # Update the game objects paths
                        multi_disc.set_new_directory_name(multi_game_folder)
                        multi_disc.cue_sheet.bin_files[0].file_path = join(multi_game_path, f"{filename_no_extension}.bin")
                        multi_disc.cue_sheet.file_path = join(multi_game_path, f"{filename_no_extension}.cue")

                        # Remove the original game directory
                        rmtree(game_path)

                # Generate LST file here
                game_path = join(multi_games[0].directory_path, multi_games[0].directory_name)
                try:
                    with open(join(game_path, "MULTIDISC.LST"), 'w') as file:
                        for multi_disc in multi_games:
                            file.write(f"{multi_disc.cue_sheet.game_name}.bin" + '\n')

                            multi_disc.multi_disc_file_present = True

                except Exception as e:
                    print(f"Error creating multi-disc file '{filename}': {e}")

                # Ensure that each disc in the collection has cover art available.
                self._copy_multi_disc_cover_art(game, multi_games)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _copy_multi_disc_cover_art(self, disc_1: Game, multi_games):

        debug_print("CHECKING COVER ART FOR MULTI-DISC GAMES...")

        if disc_1.cover_art_present:
            disc_1_bmp_path = join(disc_1.directory_path, disc_1.directory_name, f"{disc_1.cue_sheet.game_name}.bmp")

            if exists(disc_1_bmp_path):
                for multi_disc in multi_games:
                    if multi_disc.disc_number > 1 and not multi_disc.cover_art_present:
                        disc_bmp_path = join(multi_disc.directory_path, multi_disc.directory_name, f"{multi_disc.cue_sheet.game_name}.bmp")

                        copyfile(disc_1_bmp_path, disc_bmp_path)

                        if exists(disc_bmp_path):
                            multi_disc.cover_art_present = True
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _find_game_by_id(self, game_id: str) -> Game:
        game_dict = {game.id: game for game in self.game_list}
        return game_dict.get(game_id)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _find_game_by_name(self, game_name: str) -> Game:
        game_dict = {game.cue_sheet.game_name: game for game in self.game_list}
        return game_dict.get(game_name)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _remove_disc_from_game_name(self, game_name: str) -> str:
        """Check if "Disc" is in the string and remove it"""
        if search(r'\bDisc\b', game_name, IGNORECASE):
            cleaned = sub(r'\s*\(?\bDisc\s*\d+\)?', '', game_name, flags=IGNORECASE).strip()
            return cleaned
        return game_name
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _detect_cdda(self, cue_file_path: str):
        """Reads a CUE file and determines if it uses CDDA (CD Digital Audio) tracks"""
        try:
            with open(cue_file_path, 'r') as file:
                lines = file.readlines()
			
            # Count tracks and check for AUDIO tracks
            track_count = 0
            has_audio = False
			
            for line in lines:
                line = line.strip()
                if line.startswith('TRACK'):
                    track_count += 1
                    # Check if the track is an AUDIO track
                    if 'AUDIO' in line:
                        has_audio = True
			
            # CDDA is indicated by multiple tracks with at least one AUDIO track
            return track_count > 1 and has_audio
		
        except FileNotFoundError:
            print(f"Error: CUE file '{cue_file_path}' not found.")
            return False
        except Exception as e:
            print(f"Error reading CUE file: {e}")
            return False
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _merge_bin_files(self, game: Game):
        """Merge multi-bin files"""

        game_name = game.cue_sheet.game_name
        game_full_path = join(game.directory_path, game.directory_name)
        cue_full_path = join(game_full_path, game.cue_sheet.file_name)

        temp_game_dir = join(game_full_path, 'temp_dir')
        if not exists(temp_game_dir):
            try:
                mkdir(temp_game_dir)
            except OSError:
                pass

        if exists(temp_game_dir):
            self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Merging bin files')
            start_bin_merge(cue_full_path, game_name, temp_game_dir)

            temp_bin_path = join(temp_game_dir, f'{game_name}.bin')
            temp_cue_path = join(temp_game_dir, f'{game_name}.cue')
            if exists(temp_bin_path) and exists(temp_cue_path):
                remove(cue_full_path)
                
				# Remove the original multi-bin files
                for original_bin_file in game.cue_sheet.bin_files:
                    remove(original_bin_file.file_path)

                move(temp_bin_path, join(game_full_path, f'{game_name}.bin'))
                move(temp_cue_path, join(game_full_path, f'{game_name}.cue'))

            rmtree(temp_game_dir)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _rename_game(self, game: Game, new_game_name: str):
        """Rename game and associated files"""

        game_name = game.cue_sheet.game_name
        game_full_path = join(game.directory_path, game.directory_name)

        # Get the original file paths
        original_bin_file = join(game_full_path, f'{game_name}.bin')
        original_cue_file = join(game_full_path, f'{game_name}.cue')
        original_cu2_file = join(game_full_path, f'{game_name}.cu2')
        original_bmp_file = join(game_full_path, f'{game_name}.bmp')

        # Create new directory for the game
        new_filepath = join(dirname(dirname(game_full_path)), new_game_name)
        makedirs(new_filepath, exist_ok=True)

        # Move/rename the bin file
        if exists(original_bin_file):
            move(original_bin_file, join(new_filepath, f'{new_game_name}.bin'))

        # Move/rename the cue file
        if exists(original_cue_file):
            cue_path = Path(original_cue_file)
            cue_text = cue_path.read_text()
            cue_text = cue_text.replace(game_name, new_game_name)
            cue_path.write_text(cue_text)
            move(original_cue_file, join(new_filepath, f'{new_game_name}.cue'))

        # Move/rename the cu2 file
        if exists(original_cu2_file):
            move(original_cu2_file, join(new_filepath, f'{new_game_name}.cu2'))

        # Move/rename the bmp file
        if exists(original_bmp_file):
            move(original_bmp_file, join(new_filepath, f'{new_game_name}.bmp'))

        # Delete the original game directory
        rmtree(game_full_path, ignore_errors=True)

        # Update the game objects paths
        game.set_new_directory_name(new_game_name)
        game.cue_sheet.game_name = new_game_name
        game.cue_sheet.bin_files[0].file_path = join(new_filepath, f'{new_game_name}.bin')
        game.cue_sheet.file_name = f'{new_game_name}.cue'
        game.cue_sheet.file_path = join(new_filepath, f'{new_game_name}.cue')
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _game_name_validator(self, game_or_name: Union['Game', str], update_game: bool = True) -> str:
        """Validate game name length and characters"""
        if isinstance(game_or_name, Game):
            if not hasattr(game_or_name, 'cue_sheet') or not hasattr(game_or_name.cue_sheet, 'game_name'):
                raise ValueError("Game object must have a valid cue_sheet.game_name attribute")
            game_name = game_or_name.cue_sheet.game_name
        elif isinstance(game_or_name, str):
            game_name = game_or_name
        else:
            raise ValueError("Input must be a Game object or a string")

        # Handle empty or whitespace-only names
        game_name = game_name.strip()
        if not game_name:
            raise ValueError("Game name cannot be empty or whitespace-only")

        # Replace invalid characters with underscore
        sanitized_name = sub(self.INVALID_FILENAME_CHARS, '_', game_name)

        # Truncate to maximum length
        sanitized_name = sanitized_name[:self.MAX_GAME_NAME_LENGTH]

        # Update Game object if requested and input is a Game
        if update_game and isinstance(game_or_name, Game) and hasattr(game_or_name.cue_sheet, 'new_name'):
            game_or_name.cue_sheet.new_name = sanitized_name

        return sanitized_name

    def _is_multi_disc(self, game: Game):
        """Check if game is multi-disc"""
        return int(game.disc_number) > 0 if game.disc_number is not None else None

    def _is_multi_bin(self, game: Game):
        """Check if game has multiple bin files"""
        return len(game.cue_sheet.bin_files) > 1

    def _all_game_files_exist(self, game: Game):
        """Check if all required bin files exist"""
        for bin_file in game.cue_sheet.bin_files:
            if not exists(bin_file.file_path):
                return False
        return True
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    # Function to get the game name (using names from redump and the psx data-centre)
    def _get_redump_name(self, game_id: str):
        response = select(f'''SELECT name FROM games WHERE game_id = "{game_id.replace('-','_')}";''')
        if response is not None and response != []:
            game_name = response[0][0]
            return game_name

        return ''
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _get_game_name_from_cue(self, cue_path: str, include_track=False):
        """Get game name from cue sheet"""
        cue_content = read_cue_file(cue_path)
        if cue_content:
            game_name = basename(cue_content[0].filename)
            if not include_track and 'Track' in game_name:
                game_name = game_name[:game_name.rfind('(', 0) -1]
            return splitext(game_name)[0]
        return ''
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _get_game_id(self, bin_file_path: str):
        """Get unique game ID from bin file"""
        game_disc_collection = self._get_disc_collection(bin_file_path)
        return game_disc_collection[0].replace('_', '-').replace('.', '').strip() if game_disc_collection else None
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    # Function to get the unique game id from the bin file
    # Some games are multi-disc games and the bin file will have the game-id for each game in the collection
    def _get_disc_collection(self, bin_file_path: str):
        game_disc_collection = []
        line = ''
        lines_checked = 0
        
        if not exists(bin_file_path):
            return game_disc_collection

        # Open the games bin file
        with open(bin_file_path, 'rb') as bin_file:

            # Read each line of bytes (stop if we reach MAX_LINES_TO_CHECK)
            # The region-code/game-id is always located in the first few bytes of the bin file
            while line != None and lines_checked < self.MAX_LINES_TO_CHECK:  
                try:
                    line = str(next(bin_file))
                    
                    if line == None:
                        continue

                    lines_checked += 1
                    for region_code in self.REGION_CODES:

                        # Check if the line of bytes contains any known region-code
                        if region_code in line:
                            
                            # Use the region-code location to parse the game-id from the bytes of data
                            start = line.find(region_code)
                            game_id = line[start:start + 11].replace('.', '').strip()
                            
                            # Add the game-id to the collection
                            if game_id not in game_disc_collection:
                                game_disc_collection.append(game_id)
                            else:
                                raise StopIteration
                except StopIteration:
                    break
                
        return game_disc_collection
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _get_disc_number(self, game_id: str):
        """Get disc number from redump database"""
        response = select(f'''SELECT disc_number FROM games WHERE game_id = "{game_id.replace('-','_')}";''')
        return response[0][0] if response and response != [] else 0
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _copy_game_cover(self, output_path: str, game_id: str, game_name: str):
        """Copy game front cover if available"""
        response = select(f'''SELECT id FROM covers WHERE game_id = "{game_id.replace('-','_')}";''')
        if response and response != []:
            row_id = response[0][0]
            image_out_path = join(output_path, f'{game_name}.bmp')
            extract_game_cover_blob(row_id, image_out_path)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _create_game_list(self, selected_path: str):
        """Create global game list"""
        self.game_list = []
        subfolders = [f.name for f in scandir(selected_path) if f.is_dir() and not f.name.startswith('.')]

        if not subfolders:
            subfolders = [selected_path]

        debug_print('\nGAME DETAILS:\n')

        for subfolder in subfolders:
            if subfolder != "System Volume Information":
                game_directory_path = join(selected_path, subfolder)
                cue_sheets = [f for f in listdir(game_directory_path) if f.lower().endswith('.cue') and not f.startswith('.')]
                
                if cue_sheets == []:
                    cue_sheets = [f for f in listdir(game_directory_path) if f.lower().endswith('.cu2') and not f.startswith('.')]

                for cue_sheet in cue_sheets:
                    cue_sheet_path = join(game_directory_path, cue_sheet)
                    
                    game_name_from_cue = self._get_game_name_from_cue(cue_sheet_path)

                    cover_art_path = join(game_directory_path, cue_sheet[:-3])
                    cover_art_present = exists(f'{cover_art_path}bmp') or exists(f'{cover_art_path}BMP')
 
                    multi_disc_file_present = exists(join(game_directory_path, 'MULTIDISC.LST'))

                    cu2_present = exists(join(selected_path, subfolder, f'{cue_sheet[:-3]}cu2'))
                    
					# Check if the game uses CDDA audio (cu2 will be required)
                    cu2_required = self._detect_cdda(cue_sheet_path)

                    game_id = None
                    bin_files = read_cue_file(cue_sheet_path)
                    if bin_files:
                        game_id = self._get_game_id(bin_files[0].filename)

                    disc_number = 0
                    disc_collection = []
                    if game_id:
                        disc_number = self._get_disc_number(game_id)
                        disc_collection = self._get_disc_collection(join(game_directory_path, f'{game_name_from_cue}.bin'))

                    the_cue_sheet = Cuesheet(cue_sheet, cue_sheet_path, game_name_from_cue)
                    for bin_file in bin_files:
                        the_cue_sheet.add_bin_file(Binfile(basename(bin_file.filename), bin_file.filename))

					# Create the game
                    the_game = Game(subfolder, selected_path, game_id, disc_number, disc_collection, the_cue_sheet, cover_art_present, cu2_present, cu2_required, multi_disc_file_present)

                    self.game_list.append(the_game)
                    self._print_game_details(the_game)

        self.game_list.sort(key=lambda game: game.cue_sheet.game_name, reverse=False)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _print_game_details(self, game: Game):
        """Print game details for debugging"""
        game_path = join(game.directory_path, game.directory_name)
        debug_print(f'Game Path: {game_path}')
        debug_print(f'Game ID: {game.id}')
        debug_print(f'Game Name: {game.cue_sheet.game_name}')
        debug_print(f'Disc Number: {game.disc_number}')
        debug_print(f'Number of Bin Files: {len(game.cue_sheet.bin_files)}')
        if game.disc_collection:
            debug_print(f'Disc Collection: {game.disc_collection}')
        debug_print(f'Has Cover ART: {game.cover_art_present}')
        debug_print(f'CU2 Required: {game.cu2_required}')
        debug_print(f'Has CU2: {game.cu2_present}\n')
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _load_image(self, image_path: str):
        """Load and display the BMP image"""
        for widget in self.cover_art_frame.winfo_children():
            widget.destroy()

        try:
            if not isfile(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
        
            image = Image.open(image_path)
            image = image.resize((90, 90), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)
            image_label = Label(self.cover_art_frame, image=self.photo, bootstyle="primary")
            image_label.pack(pady=4, padx=4)

        except Exception as e:
            debug_print(e)
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _parse_game_list(self):
        """Parse game list and display results"""
        self._create_game_list(self.src_path.get())
        games_without_cover = []
        multi_bin_games = []
        invalid_named_games = []
        unidentified_games = []
        multi_discs = []
        multi_disc_games = []

        for game in self.game_list:
            bin_files = game.cue_sheet.bin_files

            if game.id is None:
                unidentified_games.append(game)
            if not game.cover_art_present and game.disc_number is not None and int(game.disc_number) < 2:
                games_without_cover.append(game)
            if self._is_multi_disc(game):
                multi_discs.append(game)
                if int(game.disc_number) == 1:
                    multi_disc_games.append(game)
            if len(bin_files) > 1:
                multi_bin_games.append(game)
            if len(game.cue_sheet.game_name) > self.MAX_GAME_NAME_LENGTH or '.' in game.cue_sheet.game_name:
                invalid_named_games.append(game)

        self.progress_bar_indeterminate.stop()
        self._update_progress_bar_2(0)

        md = MessageDialog(
            f'''Total Discs Found: {len(self.game_list)} \nMulti-Disc Games: {len(multi_disc_games)} \nUnidentfied Games: {len(unidentified_games)} \nMulti-bin Games: {len(multi_bin_games)} \nMissing Covers: {len(games_without_cover)} \nInvalid Game Names: {len(invalid_named_games)}''',
            title='Game Details', width=650, padding=(20, 20))
        md.show()

        self._display_game_list()
        self._update_window()
    # *****************************************************************************************************************


    # *****************************************************************************************************************
    def _display_game_list(self):
        """Display game list in treeview"""

        # Clear any existing items in the tree-view
        for item in self.treeview_game_list.get_children():
            self.treeview_game_list.delete(item)

        # Populate the tree-view using the game list
        bools = ('No', 'Yes')
        for count, game in enumerate(self.game_list):
            game_id = game.id
            game_name = game.cue_sheet.game_name
            disc_number = game.disc_number
            number_of_bins = len(game.cue_sheet.bin_files)
            name_valid = bools[len(game.cue_sheet.game_name) <= self.MAX_GAME_NAME_LENGTH and '.' not in game.cue_sheet.game_name]
            cu2_present = bools[game.cu2_present] if game.cu2_required else "N/A"

            lst_present = "N/A"
            if game.disc_number > 0:
                lst_present = "yes" if game.multi_disc_file_present else "No"

            bmp_present = bools[game.cover_art_present]
            
            self.treeview_game_list.insert(parent='', index=count, iid=count, text='',
                                        values=(game_id, game_name, disc_number, number_of_bins, name_valid, cu2_present, lst_present, bmp_present))
    # *****************************************************************************************************************


    def _prevent_hidden_files(self):
        """Prevent hidden files in file browser dialog"""
        try:
            try:
                self.window.tk.call('tk_getOpenFile', '-foobarbaz')
            except TclError:
                pass
            self.window.tk.call('set', '::tk::dialog::file::showHiddenBtn', '1')
            self.window.tk.call('set', '::tk::dialog::file::showHiddenVar', '0')
        except:
            pass

    def _update_progress_bar(self, value):
        """Update progress bar"""
        self.progress_bar['value'] = value
        if self.window:
            self.window.update()
        sleep(0.1)

    def _update_progress_bar_2(self, value):
        """Update indeterminate progress bar"""
        self.progress_bar_indeterminate['value'] = value
        if self.window:
            self.window.update()
        sleep(0.1)

    def _update_window(self):
        """Update main UI window"""
        if self.window:
            self.window.update()
        sleep(0.02)

    def _on_treeview_click(self, event):
        """Handle left-click events on the Treeview"""
        tree = event.widget
        item = tree.identify_row(event.y)
        if item:
            # Highlight the clicked row
            tree.selection_set(item)

            # Get the game name
            values = tree.item(item, "values")
            game_id = values[0]

            # Find the game object using the game ID
            the_game = self._find_game_by_id(game_id)

            # Determine the BMP image path from the cuesheet path
            bmp_path = the_game.cue_sheet.file_path[:-4] + ".bmp"

            # Display the BMP image
            self._load_image(bmp_path)

    def _scan_button_clicked(self):
        """Handle scan button click"""
        self.button_src_scan['state'] = 'disabled'
        self.progress_bar_indeterminate.start(20)
        self._parse_game_list()
        self.button_start['state'] = 'normal'

    def _browse_button_clicked(self):
        """Handle browse button click"""
        selected_path = filedialog.askdirectory(initialdir='/', title='Select Game Directory')
        self.src_path.set(selected_path)
        self.label_src.configure(text= f"  {self.src_path.get()}")
        self.button_src_scan['state'] = 'normal' if self.src_path.get() else 'disabled'

    def _start_button_clicked(self):
        """Handle start button click"""
        if self.src_path.get():
            self.button_start['state'] = 'disabled'
            self.process_games()
            self.button_start['state'] = 'normal'

    def _checkbox_changed(self):
        """Handle checkbox change"""
        if not any([self.redump_rename.get()]):
            self.button_start['state'] = 'disabled'
        elif self.src_path.get() and self.game_list:
            self.button_start['state'] = 'normal'

    def _get_stored_theme(self):
        """Get stored theme from config"""
        if exists(self.CONFIG_FILE_PATH):
            with open(self.CONFIG_FILE_PATH) as config_file:
                return load(config_file)['theme']
        else:
            return "superhero"

    def _store_selected_theme(self, theme_name):
        """Store selected theme"""
        with open(self.CONFIG_FILE_PATH, mode="w") as config_file:
            config_file.write(dumps({"theme": theme_name}))

    def _switch_theme(self, theme_name):
        """Switch UI theme"""
        style = Style()
        style.theme_use(theme_name)
        self._store_selected_theme(theme_name)

    def setup_gui(self):
        """Setup the GUI"""
        self.window = Window(title=f'PSIO Game Assistant v{self.CURRENT_REVISION}',
                               themename=self._get_stored_theme(), size=[800,660], resizable=[False, False])
        
        # Initialise Tkinter variables
        self.src_path = StringVar(self.window)
        self.dest_path = StringVar(self.window)
        self.redump_rename = BooleanVar(self.window)
        
        # Set default checkbox values
        self.redump_rename.set(False)
        
        # Menu setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)
        
        file_menu = Menu(menubar, tearoff=0)
        sub_menu = Menu(file_menu, tearoff=0)
        themes = ['cyborg', 'darkly', 'vapor', 'superhero', 'solar', 'morph', 'sandstone', 'simplex', 'yeti']
        for theme in themes:
            sub_menu.add_command(label=theme, command=lambda t=theme: self._switch_theme(t))
        
        file_menu.add_cascade(label="Color Themes", menu=sub_menu)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.window.destroy)
        menubar.add_cascade(label="File", menu=file_menu, underline=0)
        
        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label='About')
        menubar.add_cascade(label="Help", menu=help_menu, underline=0)

        # Browse frame
        browse_frame = Labelframe(self.window, text='SD Root', bootstyle="primary")
        browse_frame.place(x=15, y=10, width=770, height=110)
        
        self.label_src = Label(self.window, text=self.src_path.get(), width=60, borderwidth=2, relief='solid', bootstyle="primary", font=("Arial", 11))
        self.label_src.place(x=30, y=35, width=600, height=30)
        
        button_src_browse = Button(self.window, text='Browse', bootstyle="primary", command=self._browse_button_clicked)
        button_src_browse.place(x=640, y=35, width=130, height=30)
        
        self.progress_bar_indeterminate = Floodgauge(font=(None, 14, 'bold'), mask='', mode='indeterminate')
        self.progress_bar_indeterminate.place(x=30, y=75, width=600, height=30)
        
        self.button_src_scan = Button(self.window, text='Scan', command=self._scan_button_clicked, state=DISABLED)
        self.button_src_scan.place(x=640, y=75, width=130, height=30)

        # Game list frame
        game_list_frame = Labelframe(self.window, text='Files', bootstyle="primary")
        game_list_frame.place(x=15, y=140, width=770, height=350)
        
        self.treeview_game_list = Treeview(self.window, bootstyle='primary')
        self.treeview_game_list.bind("<Button-1>", self._on_treeview_click)

        self.treeview_game_list['columns'] = ('ID', 'Name', 'Disc', 'Bin Files', 'Name Valid', 'CU2', 'LST', 'BMP')
        self.treeview_game_list.column('#0', width=0, stretch=NO)
        self.treeview_game_list.column('ID', anchor=CENTER, width=75)
        self.treeview_game_list.column('Name', anchor=CENTER, width=330)
        self.treeview_game_list.column('Disc', anchor=CENTER, width=60)
        self.treeview_game_list.column('Bin Files', anchor=CENTER, width=60)
        self.treeview_game_list.column('Name Valid', anchor=CENTER, width=75)
        self.treeview_game_list.column('CU2', anchor=CENTER, width=40)
        self.treeview_game_list.column('LST', anchor=CENTER, width=40)
        self.treeview_game_list.column('BMP', anchor=CENTER, width=40)
        
        self.treeview_game_list.heading('#0', text='', anchor=CENTER)
        self.treeview_game_list.heading('ID', text='ID', anchor=CENTER)
        self.treeview_game_list.heading('Name', text='Name', anchor=CENTER)
        self.treeview_game_list.heading('Disc', text='Disc', anchor=CENTER)
        self.treeview_game_list.heading('Bin Files', text='Bin Files', anchor=CENTER)
        self.treeview_game_list.heading('Name Valid', text='Name Valid', anchor=CENTER)
        self.treeview_game_list.heading('CU2', text='CU2', anchor=CENTER)
        self.treeview_game_list.heading('LST', text='LST', anchor=CENTER)
        self.treeview_game_list.heading('BMP', text='BMP', anchor=CENTER)
        
        scrollbar_game_list = Scrollbar(self.window, bootstyle="primary-round", orient=VERTICAL, 
                                      command=self.treeview_game_list.yview)
        
        self.treeview_game_list.configure(yscroll=scrollbar_game_list.set)
        self.treeview_game_list.place(x=30, y=160, width=730, height=310)
        scrollbar_game_list.place(x=760, y=160, height=310)

        # Cover art frame
        self.cover_art_frame = Labelframe(self.window, text='BMP', bootstyle="primary")
        self.cover_art_frame.place(x=15, y=510, width=130, height=130)
        
        # Process frame
        progress_frame = Labelframe(self.window, text='Process Files', bootstyle="primary")

        progress_frame.place(x=170, y=510, width=615, height=130)

        Checkbutton(self.window, text='Redump Rename', bootstyle="round-toggle", takefocus=0, 
                   variable=self.redump_rename, command=self._checkbox_changed).place(x=190, y=540)
        
        self.progress_bar = Floodgauge(font=(None, 14, 'bold'), mask='', mode='determinate')
        self.progress_bar.place(x=190, y=570, width=440, height=30)

        self.button_start = Button(self.window, text='Start', command=self._start_button_clicked, state=DISABLED)
        self.button_start.place(x=640, y=570, width=130, height=30)
        
        self.label_progress = Label(self.window, text=self.PROGRESS_STATUS, width=120, bootstyle="primary")
        self.label_progress.place(x=190, y=605, width=550, height=30)
        
        self.label_progress.after(1000, ensure_database_exists)

        self._prevent_hidden_files()

    def run(self):
        """Run the application"""
        self.setup_gui()
        self.window.mainloop()

if __name__ == "__main__":
    app = PSIOGameAssistant()
    app.run()
