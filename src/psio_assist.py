#!/usr/bin/env python3
#
#  psio-assist
#
#  This is an open-source application for preparing PlayStation games for use with a PSIO device
#
#  Features:
#  * Runs in batch mode, processing all of the games that have been selected
#  * Merge any games that have multiple bin files into a single bin file
#  * Update the cue sheet file to only contain a single bin file
#  * Detect games that use CCDA audio and generate a cu2 file
#  * Fix any game names that are too long or contain invalid characters
#  * Add a bmp image file for each game in the correct resolution for the PSIO menu
#  * Detect multi-disc games and organise them into a single directory and generate a multi-disc lst file
#  * Patch LibCrypt games
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
import sys
from os import listdir, scandir, mkdir, remove
from os.path import exists, join, dirname, basename, splitext, abspath, isfile
from time import sleep
from json import load, dumps
from typing import Union
from argparse import ArgumentParser
from re import search, sub, IGNORECASE
from shutil import copyfile, move, rmtree
from tkinter import Menu, filedialog, StringVar, BooleanVar, TclError, PhotoImage
from ttkbootstrap import Window, Floodgauge, Treeview, Style, Scrollbar, Labelframe, Label, Button, Checkbutton, NO, CENTER, VERTICAL
from ttkbootstrap.dialogs import MessageDialog
from ttkbootstrap.constants import DISABLED
from pathlib2 import Path

# Local imports
from game_files import Game, Cuesheet, Binfile
from binmerge import set_binmerge_error_log_path, start_bin_merge, read_cue_file
from cue2cu2 import set_cu2_error_log_path, start_cue2cu2
from ppf_patcher import set_ppf_debug_mode, open_files_for_patching, ppf_version, apply_ppf1_patch, apply_ppf2_patch, apply_ppf3_patch
from db import set_database_path, ensure_database_exists, get_redump_name, get_disc_number, get_libcrypt_status, libcrypt_patch_available, copy_game_cover, copy_libcrypt_patch


class PSIOGameAssistant:
    REGION_CODES = ['DTLS_', 'SCES_', 'SLES_', 'SLED_', 'SCED_', 'SCUS_',
                    'SLUS_', 'SLPS_', 'SCAJ_', 'SLKA_', 'SLPM_', 'SCPS_',
                    'SCPM_', 'PCPX_', 'PAPX_', 'PTPX_', 'LSP0_', 'LSP1_',
                    'LSP2_', 'LSP9_', 'SIPS_', 'ESPM_', 'SCZS_', 'SPUS_',
                    'PBPX_', 'LSP_']

    CURRENT_REVISION = 0.3
    PROGRESS_STATUS = 'Status:'
    MAX_GAME_NAME_LENGTH = 56
    INVALID_FILENAME_CHARS = r'[.\\/:*?"<>|]'
    MAX_REDUMP_NAME_LENGTH = 47
    MAX_LINES_TO_CHECK = 300
    GAME_ID_LENGTH = 11

    def __init__(self, args=None):
        """Initialise the PSIO Game Assistant application"""

        self.game_list = []
        self.script_root_dir = Path(abspath(dirname(sys.argv[0])))
        self.covers_path = join(dirname(self.script_root_dir), 'covers')
        self.error_log_file = join(dirname(self.script_root_dir), 'errors.txt')
        self.config_file_path = join(self.script_root_dir, 'config')

        # Set the error log paths for the Bin-Merge and CUE2CU2 processes
        set_cu2_error_log_path(self.error_log_file)
        set_binmerge_error_log_path(self.error_log_file)

        # Initialise variables
        self.args = args
        self.window = None
        self.icon = None
        self.src_path = None
        self.dest_path = None
        self.redump_rename = None

        # GUI elements
        self.label_progress = None
        self.progress_bar = None
        self.button_start = None
        self.treeview_game_list = None
        self.label_src = None
        self.cover_art_frame = None

        # Set the database and icon file paths
        self.database_name = "psio_assist.db"
        self.icon_path = self._resource_path("icon.ico")
        self.database_path = self._resource_path("data")
        set_database_path(self.database_path, self.database_name)

        print(f'Database path: {self.database_path}')
        print(f'Database path exists: {exists(self.database_path)}')
        print(f'Icon path: {self.icon_path}')
        print(f'Icon path exists: {exists(self.icon_path)}')

        # Set debug mode based on the parsed arguments
        self.debug_mode = args.debug if args else False
        set_ppf_debug_mode(self.debug_mode)

        self._debug_print(f'\nPSIO Game Assistant v{self.CURRENT_REVISION}')


    # ************************************************************************************
    def _resource_path(self, relative_path):
        """Get the absolute path to resources, works for scripts and the bundled exe"""
        if hasattr(sys, '_MEIPASS'):
            # Running as an exe
            base_path = sys._MEIPASS
        else:
            # Running as a script
            base_path = abspath(".")
        return join(base_path, relative_path)
    # ************************************************************************************


    # ************************************************************************************
    def _debug_print(self, the_string: str):
        """Print debug information to the console"""
        if self.debug_mode:
            print(the_string)
    # ************************************************************************************


    # ************************************************************************************
    def process_games(self):
        """Process the games in the game list"""

        self._debug_print('\nPROCESSING GAMES...')

        # Loop through all of the Game objects in the game list
        for game in self.game_list:

            # Display the game name in the progress label
            game_name = game.get_cue_sheet().get_game_name()
            self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Processing - {game_name}')

            self._debug_print('\n***********************************************************')
            self._debug_print(f'GAME_ID: {game.get_id()}')
            self._debug_print(f'GAME_NAME: {game_name}')

            # Merge multi-bin files
            self._merge_multi_bin_files(game)

            # Generate CU2 file for games with CCDA audio
            self._generate_cu2_file(game)

            # Rename the game using the game name from the Redump project
            self._rename_game_using_redump(game)

            # Validate the game name
            self._validate_game_name(game)

            # Add the game cover art
            self._add_game_cover_art(game)

            # Apply LibCrypt PPF patch
            self._apply_libcrypt_patch(game)

            self._debug_print('***********************************************************\n')

        # Generate multi-disc games after all of the other processes have been completed
        self._generate_multidisc_files()

        self.label_progress.configure(text=self.PROGRESS_STATUS)

        # Update the game list in the GUI
        self._display_game_list()

        self._debug_print('Processing finished!\n')
    # ************************************************************************************


    # ************************************************************************************
    def _merge_multi_bin_files(self, game: Game):
        """Merge multi-bin files"""
        game_name = game.get_cue_sheet().get_game_name()
        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        cue_full_path = join(game_full_path, game.get_cue_sheet().get_file_name())

        if len(game.get_cue_sheet().get_bin_files()) > 1:
            self._debug_print('MERGING BIN FILES...')
            label_text = f'{self.PROGRESS_STATUS} Merging bin files - {game_name}'
            self.label_progress.configure(text=label_text)
            self._merge_bin_files(game)

            bin_path = cue_full_path[:-4] + ".bin"
            if exists(bin_path):
                game.get_cue_sheet().set_bin_files([])
                game.get_cue_sheet().add_bin_file(Binfile(f"{game_name}.bin", bin_path))
    # ************************************************************************************


    # ************************************************************************************
    def _generate_cu2_file(self, game: Game):
        """Generate CU2 file for games with CCDA audio"""
        game_name = game.get_cue_sheet().get_game_name()
        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        cue_full_path = join(game_full_path, game.get_cue_sheet().get_file_name())

        if game.get_cu2_required() and not game.get_cu2_present():
            self._debug_print('GENERATING CU2...')
            label_text = f'{self.PROGRESS_STATUS} Generating cu2 file - {game_name}'
            self.label_progress.configure(text=label_text)
            start_cue2cu2(cue_full_path, f'{game_name}.bin')

            cu2_path = cue_full_path[:-4] + ".cu2"
            if exists(cu2_path):
                game.set_cu2_present(True)
    # ************************************************************************************


    # ************************************************************************************
    def _rename_game_using_redump(self, game: Game):
        """Rename the game using the game name from the Redump project"""
        if self.redump_rename.get():
            game_id = game.get_id()
            game_name = game.get_cue_sheet().get_game_name()
            self._debug_print('RENAMING THE GAME FILES USING REDUMP...')
            self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Renaming - {game_name}')

            redump_game_name = get_redump_name(game_id)
            self._debug_print(f'Redump Game Name: {redump_game_name}')

            if redump_game_name is not None and redump_game_name != "":
                redump_name = self._game_name_validator(redump_game_name)

                self._debug_print(f'Validated Redump Game Name: {redump_name}')
                self._rename_game(game, redump_name)
    # ************************************************************************************


    # ************************************************************************************
    def _validate_game_name(self, game: Game):
        """Validate the game name"""
        game_name = game.get_cue_sheet().get_game_name()
        if len(game_name) > self.MAX_GAME_NAME_LENGTH or '.' in game_name:
            self._debug_print('FIXING THE GAME NAME...')
            label_text = f'{self.PROGRESS_STATUS} Validating name - {game_name}'
            self.label_progress.configure(text=label_text)

            new_game_name = self._game_name_validator(game)
            self._debug_print(f'Fixed Game Name: {new_game_name}')
            if new_game_name != game_name:
                self._rename_game(game, new_game_name)
    # ************************************************************************************


    # ************************************************************************************
    def _add_game_cover_art(self, game: Game):
        """Add the game cover art"""
        game_id = game.get_id()
        game_name = game.get_cue_sheet().get_game_name()

        if game.get_cover_art_present():
            return

        self._debug_print('ADDING THE GAME COVER ART...')
        self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Adding cover art - {game_name}')

        # Get the game cover art from the database and copy it to the local directory
        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        copy_game_cover(game_full_path, game_id, game_name)

        # If the game cover has been copied, update the game object cover details
        if exists(join(game_full_path, f'{game_name}.bmp')):
            game.set_cover_art_present(True)
    # ************************************************************************************


    # ************************************************************************************
    def _apply_libcrypt_patch(self, game: Game):
        """Apply LibCrypt PPF patch"""

        if not game.get_libcrypt_required():
            return

        if libcrypt_patch_available(game.get_id()):
            self._debug_print('PATCHING BIN FILE...')

            # Get the LibCrypt PPF patch from the database and copy it to the local directory
            game_full_path = join(game.get_directory_path(), game.get_directory_name())
            copy_libcrypt_patch(game_full_path, game.get_id())

            game_path = join(game.get_directory_path(), game.get_directory_name())
            bin_path = game.get_cue_sheet().get_bin_files()[0].get_file_path()
            ppf_path = f"{join(game_path, game.get_id())}.ppf"

            # If the PPF patch file has been copied, patch the BIN file
            if exists(ppf_path):
                bin_file, ppf_file = open_files_for_patching(bin_path, ppf_path)

                self._debug_print("Applying patch...")
                with bin_file, ppf_file:
                    version = ppf_version(ppf_file)
                    if version == 1:
                        apply_ppf1_patch(ppf_file, bin_file)
                    elif version == 2:
                        apply_ppf2_patch(ppf_file, bin_file)
                    elif version == 3:
                        apply_ppf3_patch(ppf_file, bin_file)

                # Delete the PPF patch file after it has been applied to the BIN file
                remove(ppf_path)
    # ************************************************************************************


    # ************************************************************************************
    def _generate_multidisc_files(self):
        """Generate MULTIDISC.LST file for all multi-disc games"""
        multi_disc_games = [game for game in self.game_list if game.get_disc_number() > 0]
        if not multi_disc_games:
            return

        self._debug_print('\nGENERATING MULTI-DISC FILES...\n')
        self._process_multi_disc_games()
    # ************************************************************************************


    # ************************************************************************************
    def _process_multi_disc_games(self):
        """Process each game in the game list to handle multi-disc collections."""
        for game in self.game_list:
            if not self._is_first_disc_without_multidisc(game):
                continue

            self._debug_print(f'Game name: {game.get_cue_sheet().get_game_name()}')
            self._debug_print(f'Game disc collection: {game.get_disc_collection()}')

            multi_games = self._collect_multi_games(game)
            if len(multi_games) <= 1:
                continue

            new_game_path = self._create_multi_disc_folder(multi_games)
            self._process_disc_files(multi_games, new_game_path)
            self._generate_lst_file(multi_games)
            self._copy_multi_disc_cover_art(game, multi_games)
    # ************************************************************************************


    # ************************************************************************************
    def _is_first_disc_without_multidisc(self, game):
        """Check if the game is the first disc without a multi-disc file."""
        return game.get_disc_number() == 1 and not game.get_multi_disc_file_present()
    # ************************************************************************************


    # ************************************************************************************
    def _collect_multi_games(self, game):
        """Collect all games in the disc collection."""
        return [
            self._find_game_by_id(game_id.replace("_", "-"))
            for game_id in game.get_disc_collection()
        ]
    # ************************************************************************************


    # ************************************************************************************
    def _create_multi_disc_folder(self, multi_games):
        """Create a folder for the multi-disc game collection."""
        game_folder = self._remove_disc_from_name(multi_games[0].get_cue_sheet().get_game_name())
        new_game_path = join(multi_games[0].get_directory_path(), game_folder)
        self._debug_print(f'\nCreating multi-disc folder: {new_game_path}')
        mkdir(new_game_path)
        return new_game_path if exists(new_game_path) else None
    # ************************************************************************************


    # ************************************************************************************
    def _process_disc_files(self, multi_games, new_game_path):
        """Move files for each disc and update game paths."""
        game_folder = self._remove_disc_from_name(multi_games[0].get_cue_sheet().get_game_name())
        for multi_disc in multi_games:
            disc_path = join(multi_disc.get_directory_path(), multi_disc.get_directory_name())
            self._debug_print(f'disc_path: {disc_path}')

            for filename in listdir(disc_path):
                source_path = join(disc_path, filename)
                target_path = join(new_game_path, filename)
                file_no_ext = splitext(filename)[0]

                self._move_file(source_path, target_path)
                self._update_game_paths(multi_disc, new_game_path, game_folder, file_no_ext)

            rmtree(disc_path)
    # ************************************************************************************


    # ************************************************************************************
    def _update_game_paths(self, multi_disc: Game, game_path: str, game_folder: str, file_no_ext: str):
        """Update Game object paths"""
        multi_disc.set_directory_name(game_folder)

        bin_path = join(game_path, f"{file_no_ext}.bin")
        cue_path = join(game_path, f"{file_no_ext}.cue")

        multi_disc.get_cue_sheet().get_bin_files()[0].set_file_path(bin_path)
        multi_disc.get_cue_sheet().set_file_path(cue_path)
    # ************************************************************************************


    # ************************************************************************************
    def _move_file(self, source_path: str, target_path: str):
        """Move a file from source to destination"""

        # Ensure that we only move files and not directories
        if isfile(source_path):
            try:
                move(source_path, target_path)
            except OSError as error:
                print(f"Error moving {source_path}: {error}")
    # ************************************************************************************


    # ************************************************************************************
    def _generate_lst_file(self, multi_games: list[Game]):
        """Generate LST file"""
        game_path = join(multi_games[0].get_directory_path(), multi_games[0].get_directory_name())
        try:
            with open(join(game_path, "MULTIDISC.LST"), 'w', encoding="utf-8") as file:
                for multi_disc in multi_games:
                    file.write(f"{multi_disc.get_cue_sheet().get_game_name()}.bin" + '\n')

                    # Update the Game object to show that it now has an associated LST file
                    multi_disc.set_multi_disc_file_present(True)

        except OSError as error:
            print(f"Error creating multi-disc file: {error}")
    # ************************************************************************************


    # ************************************************************************************
    def _copy_multi_disc_cover_art(self, disc_1: Game, multi_games):
        """Duplicate the cover art from disc 1 for each of the multi-disc games, if missing"""

        self._debug_print("CHECKING COVER ART FOR MULTI-DISC GAME...")

        if disc_1.get_cover_art_present():
            # Get the cover art for disc 1
            disc_1_path = join(disc_1.get_directory_path(), disc_1.get_directory_name())
            disc_1_bmp_path = join(disc_1_path, f"{disc_1.get_cue_sheet().get_game_name()}.bmp")

            if exists(disc_1_bmp_path):

                # Loop through the other discs in the collection and duplicate disc 1 cover art
                for multi_disc in multi_games:
                    if multi_disc.get_disc_number() > 1 and not multi_disc.get_cover_art_present():

                        game_dir_path = multi_disc.get_directory_path()
                        game_dir_name = multi_disc.get_directory_name()
                        game_name = multi_disc.get_cue_sheet().get_game_name()

                        disc_path = join(game_dir_path, game_dir_name)
                        disc_bmp_path = join(disc_path, f"{game_name}.bmp")

                        copyfile(disc_1_bmp_path, disc_bmp_path)

                        # Update the Game object to indicate that it now has a cover art file
                        if exists(disc_bmp_path):
                            multi_disc.set_cover_art_present(True)
    # ************************************************************************************


    # ************************************************************************************
    def _find_game_by_id(self, game_id: str) -> Game:
        """Return the Game object from teh game list with the specified game ID"""
        game_dict = {game.get_id(): game for game in self.game_list}
        return game_dict.get(game_id)
    # ************************************************************************************


    # ************************************************************************************
    def _find_game_by_name(self, game_name: str) -> Game:
        """Return the Game object from teh game list with the specified game name"""
        game_dict = {game.get_cue_sheet().get_game_name(): game for game in self.game_list}
        return game_dict.get(game_name)
    # ************************************************************************************


    # ************************************************************************************
    def _remove_disc_from_name(self, game_name: str) -> str:
        """Check if "Disc" is in the string and remove it"""
        if search(r'\bDisc\b', game_name, IGNORECASE):
            cleaned = sub(r'\s*\(?\bDisc\s*\d+\)?', '', game_name, flags=IGNORECASE).strip()
            return cleaned
        return game_name
    # ************************************************************************************


    # ************************************************************************************
    def _detect_cdda(self, cue_file_path: str):
        """Reads a CUE file and determines if it uses CDDA (CD Digital Audio) tracks"""
        try:
            with open(cue_file_path, 'r', encoding="utf-8") as file:
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
        except OSError as error:
            print(f"Error reading CUE file: {error}")
            return False
    # ************************************************************************************


    # ************************************************************************************
    def _merge_bin_files(self, game: Game):
        """Merge multi-bin files"""

        # Get the game info
        game_name = game.get_cue_sheet().get_game_name()
        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        cue_full_path = join(game_full_path, game.get_cue_sheet().get_file_name())

        # Create a temporary directory to use whilst merging the bin files
        temp_game_dir = join(game_full_path, 'temp_dir')
        if not exists(temp_game_dir):
            try:
                mkdir(temp_game_dir)
            except OSError:
                pass

        if exists(temp_game_dir):

            # Merge the multiple BIN files into a single BIN file
            self.label_progress.configure(text=f'{self.PROGRESS_STATUS} Merging bin files')
            start_bin_merge(cue_full_path, game_name, temp_game_dir)

            # Check if the single Bin file has been generated
            temp_bin_path = join(temp_game_dir, f'{game_name}.bin')
            temp_cue_path = join(temp_game_dir, f'{game_name}.cue')
            if exists(temp_bin_path) and exists(temp_cue_path):

                # Remove the original CUE file
                remove(cue_full_path)

				# Remove the original multi-bin files
                for original_bin_file in game.get_cue_sheet().get_bin_files():
                    remove(original_bin_file.get_file_path())

                # Move the merged Bin file and the newly generated CUE file into the game directory
                move(temp_bin_path, join(game_full_path, f'{game_name}.bin'))
                move(temp_cue_path, join(game_full_path, f'{game_name}.cue'))

            rmtree(temp_game_dir)
    # ************************************************************************************


    # ************************************************************************************
    def _rename_game(self, game: Game, new_game_name: str):
        """Rename game and associated files"""

        # Get the current game name from the CUE file
        game_name = game.get_cue_sheet().get_game_name()

        # If the game name has not changed
        if game_name == new_game_name:
            return

        self._debug_print(f'Renaming game from "{game_name}" to "{new_game_name}"')

        game_full_path = join(game.get_directory_path(), game.get_directory_name())

        # Get the original file paths
        original_bin_file = join(game_full_path, f'{game_name}.bin')
        original_cue_file = join(game_full_path, f'{game_name}.cue')
        original_cu2_file = join(game_full_path, f'{game_name}.cu2')
        original_bmp_file = join(game_full_path, f'{game_name}.bmp')

        # Create new directory for the game
        new_filepath = join(dirname(game_full_path), new_game_name)
        mkdir(new_filepath)
        if not exists(new_filepath):
            print(f"Error creating directory: {new_filepath}")
            return

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

        # Update the game objects paths
        game.set_directory_name(new_game_name)
        game.get_cue_sheet().set_game_name(new_game_name)
        game.get_cue_sheet().get_bin_files()[0].set_file_path(join(new_filepath, f'{new_game_name}.bin'))
        game.get_cue_sheet().set_file_name(f'{new_game_name}.cue')
        game.get_cue_sheet().set_file_path(join(new_filepath, f'{new_game_name}.cue'))

        # Delete the original game directory
        rmtree(game_full_path, ignore_errors=True)
    # ************************************************************************************


    # ************************************************************************************
    def _game_name_validator(self, game_or_name: Union['Game', str], update_game: bool = True) -> str:
        """Validate game name length and characters"""

        # Ensure that a Game object or string have been passed
        if isinstance(game_or_name, Game):
            if not hasattr(game_or_name, 'cue_sheet') or not hasattr(game_or_name.get_cue_sheet(), 'game_name'):
                raise ValueError("Game object must have a valid cue_sheet.game_name attribute")
            game_name = game_or_name.get_cue_sheet().get_game_name()
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
        if update_game and isinstance(game_or_name, Game) and hasattr(game_or_name.get_cue_sheet(), 'new_name'):
            game_or_name.get_cue_sheet().set_new_name(sanitized_name)

        return sanitized_name
    # ************************************************************************************


    # ************************************************************************************
    def _is_multi_disc(self, game: Game):
        """Check if game is multi-disc"""
        return int(game.get_disc_number()) > 0 if game.get_disc_number() is not None else None
    # ************************************************************************************


    # ************************************************************************************
    def _is_multi_bin(self, game: Game):
        """Check if game has multiple bin files"""
        return len(game.get_cue_sheet().get_bin_files()) > 1
    # ************************************************************************************


    # ************************************************************************************
    def _all_game_files_exist(self, game: Game):
        """Check if all required bin files exist"""
        for bin_file in game.get_cue_sheet().get_bin_files():
            if not exists(bin_file.get_file_path()):
                return False
        return True
    # ************************************************************************************


    # ************************************************************************************
    def _get_game_name_from_cue(self, cue_path: str, include_track=False):
        """Get game name from the cue sheet"""
        cue_content = read_cue_file(cue_path)
        if cue_content:
            game_name = basename(cue_content[0].filename)
            if not include_track and 'Track' in game_name:
                game_name = game_name[:game_name.rfind('(', 0) -1]
            return splitext(game_name)[0]
        return ''
    # ************************************************************************************


    # ************************************************************************************
    def _get_game_id(self, bin_file_path: str):
        """Get the unique game ID from BIN file"""
        game_disc_collection = self._get_disc_collection(bin_file_path)
        return game_disc_collection[0].replace('_', '-').replace('.', '').strip() if game_disc_collection else None
    # ************************************************************************************


    # ************************************************************************************
    def _get_disc_collection(self, bin_file_path: str):
        """
        Parse the unique game id from the BIN file
        Some games are multi-disc and the BIN file will have the id for each game in the collection
        """
        game_disc_collection = []
        line = ''
        lines_checked = 0

        if not exists(bin_file_path):
            return game_disc_collection

        # Open the games BIN file
        with open(bin_file_path, 'rb') as bin_file:

            # Read each line of bytes (stop if we reach MAX_LINES_TO_CHECK)
            # The game-id is always located in the first 50-100 bytes of the BIN file
            while line is not None and lines_checked < self.MAX_LINES_TO_CHECK:
                try:
                    line = str(next(bin_file))

                    if line is None:
                        continue

                    lines_checked += 1
                    for region_code in self.REGION_CODES:

                        # Check if the line of bytes contains any known region-code
                        if region_code in line:

                            # Use the region-code offset in the BIN file to parse the game-id
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
    # ************************************************************************************


    # ************************************************************************************
    def _create_game_list(self, selected_path: str):
        """Create and populate the global game list."""
        self.game_list = []
        sub_folders = self._get_sub_folders(selected_path)
        self._debug_print('\nGAME DETAILS:\n')

        for sub_folder in sub_folders:
            self._process_sub_folder(selected_path, sub_folder)

        self._sort_game_list()
    # ************************************************************************************


    # ************************************************************************************
    def _process_sub_folder(self, selected_path: str, sub_folder: str):
        """Process a single sub-folder to extract game information and add to game list."""
        game_directory_path = join(selected_path, sub_folder)
        cue_sheets = self._find_cue_sheets(game_directory_path)

        for cue_sheet in cue_sheets:
            game = self._create_game_from_cue(game_directory_path, cue_sheet, sub_folder, selected_path)
            if game:
                self.game_list.append(game)
                self._print_game_details(game)
    # ************************************************************************************


    # ************************************************************************************
    def _find_cue_sheets(self, game_directory_path: str) -> list:
        """Find CUE or CU2 files in the specified directory."""
        cue_sheets = [
            f for f in listdir(game_directory_path)
            if f.lower().endswith('.cue') and not f.startswith('.')
        ]

        if not cue_sheets:
            cue_sheets = [
                f for f in listdir(game_directory_path)
                if f.lower().endswith('.cu2') and not f.startswith('.')
            ]

        return cue_sheets
    # ************************************************************************************


    # ************************************************************************************
    def _create_game_from_cue(self, game_directory_path: str, cue_sheet: str, sub_folder: str, selected_path: str) -> Game:
        """Create a Game object from a CUE sheet."""
        cue_sheet_path = join(game_directory_path, cue_sheet)
        game_name_from_cue = self._get_game_name_from_cue(cue_sheet_path)

        # Check for cover art
        cover_art_path = join(game_directory_path, cue_sheet[:-3])
        cover_art_present = exists(f'{cover_art_path}bmp') or exists(f'{cover_art_path}BMP')

        # Check for multi-disc and CU2 files
        multi_disc_file_present = exists(join(game_directory_path, 'MULTIDISC.LST'))
        cu2_present = exists(join(game_directory_path, f'{cue_sheet[:-3]}cu2'))
        cu2_required = self._detect_cdda(cue_sheet_path)

        # Get game ID and disc information
        bin_files = read_cue_file(cue_sheet_path)
        game_id = self._get_game_id(bin_files[0].filename) if bin_files else None
        disc_number = get_disc_number(game_id) if game_id else 0
        bin_path = join(game_directory_path, f'{game_name_from_cue}.bin')
        disc_collection = self._get_disc_collection(bin_path) if game_name_from_cue else []

        # Get libcrypt status
        libcrypt_required = get_libcrypt_status(game_id) if game_id else False

        # Create Cuesheet and associated Binfile objects
        the_cue_sheet = Cuesheet(cue_sheet, cue_sheet_path, game_name_from_cue)
        if bin_files:
            for bin_file in bin_files:
                the_cue_sheet.add_bin_file(Binfile(basename(bin_file.filename), bin_file.filename))

        # Create and return the Game object
        return Game(
            sub_folder, selected_path, game_id, disc_number, disc_collection,
            the_cue_sheet, cover_art_present, cu2_present, cu2_required,
            multi_disc_file_present, libcrypt_required
        )
    # ************************************************************************************


    # ************************************************************************************
    def _sort_game_list(self):
        """Sort the game list alphabetically by game name."""
        self.game_list.sort(key=lambda game: game.get_cue_sheet().get_game_name(), reverse=False)
    # ************************************************************************************


    # ************************************************************************************
    def _get_sub_folders(self, selected_path: str) -> list:
        """Get a list of sub-folders in the selected source directory"""

        sub_folders = [
            f.name for f in scandir(selected_path)
            if f.is_dir()
            and not f.name.startswith('.')
            and f.name != 'System Volume Information'
        ]

        # If there are no sub-directories use the selected directory to search for files
        if not sub_folders:
            sub_folders = [selected_path]

        return sub_folders
    # ************************************************************************************


    # ************************************************************************************
    def _print_game_details(self, game: Game):
        """Print game details for debugging"""
        game_path = join(game.get_directory_path(), game.get_directory_name())
        self._debug_print(f'Game Path: {game_path}')
        self._debug_print(f'Game ID: {game.get_id()}')
        self._debug_print(f'Game Name: {game.get_cue_sheet().get_game_name()}')
        self._debug_print(f'Disc Number: {game.get_disc_number()}')
        self._debug_print(f'Number of Bin Files: {len(game.get_cue_sheet().get_bin_files())}')
        if game.get_disc_collection():
            self._debug_print(f'Disc Collection: {game.get_disc_collection()}')
        self._debug_print(f'Has Cover ART: {game.get_cover_art_present()}')
        self._debug_print(f'CU2 Required: {game.get_cu2_required()}')
        self._debug_print(f'Has CU2: {game.get_cu2_present()}\n')
    # ************************************************************************************


    # ************************************************************************************
    def _parse_game_list(self):
        """Parse game list and display results"""

        # Create the game list
        self._create_game_list(self.src_path.get())

        unidentified_games = 0
        games_without_cover = 0
        multi_discs = 0
        multi_disc_games = 0
        multi_bin_games = 0
        invalid_named_games = 0

        # Loop through the game list
        for game in self.game_list:
            bin_files = game.get_cue_sheet().get_bin_files()

            # Increment the unidentified games variable
            if game.get_id() is None:
                unidentified_games +=1

            # Increment the games without covers variable
            disc_number = game.get_disc_number()
            if not game.get_cover_art_present() and disc_number and int(disc_number) < 2:
                games_without_cover +=1

            # Increment the multi discs variable
            if self._is_multi_disc(game):
                multi_discs +=1

                # Increment the multi disc games variable
                if int(disc_number) == 1:
                    multi_disc_games +=1

            # Increment the multi-bin files variable
            if len(bin_files) > 1:
                multi_bin_games +=1

            # Increment the invalid game names variable
            game_name = game.get_cue_sheet().get_game_name()
            if len(game_name) > self.MAX_GAME_NAME_LENGTH or '.' in game_name:
                invalid_named_games +=1

        # Display a message dialog box showing the counts  
        message = (
            f"Total Discs Found: {len(self.game_list)}\n"
            f"Multi-Disc Games: {multi_disc_games}\n"
            f"Unidentified Games: {unidentified_games}\n"
            f"Multi-bin Games: {multi_bin_games}\n"
            f"Missing Covers: {games_without_cover}\n"
            f"Invalid Game Names: {invalid_named_games}"
        )

        md = MessageDialog(
            message,
            title='Game Details',
            width=650,
            padding=(20, 20)
        )
        md.show()

        self._display_game_list()
        self._update_window()
    # ************************************************************************************


    # ************************************************************************************
    def _display_game_list(self):
        """Display game list in treeview"""

        # Clear any existing items in the tree-view
        for item in self.treeview_game_list.get_children():
            self.treeview_game_list.delete(item)

        # Populate the tree-view using the game list
        bools = ('No', 'Yes')
        for count, game in enumerate(self.game_list):
            game_id = game.get_id()
            game_name = game.get_cue_sheet().get_game_name()
            disc_number = game.get_disc_number()
            number_of_bins = len(game.get_cue_sheet().get_bin_files())
            name_valid = bools[len(game.get_cue_sheet().get_game_name()) <= self.MAX_GAME_NAME_LENGTH and '.' not in game.get_cue_sheet().get_game_name()]
            cu2_present = bools[game.get_cu2_present()] if game.get_cu2_required() else "*"

            # Check if the games is a multi-disc game and if an LST file is available
            lst_present = "*"
            if game.get_disc_number() > 0:
                lst_present = "yes" if game.get_multi_disc_file_present() else "No"

            # Check if the cover art is available
            bmp_present = bools[game.get_cover_art_present()]

            # Check if the game requires LibCrypt patching and if a patch is available
            patch_available = "*"
            if game.get_libcrypt_required():
                patch_available = "Yes" if libcrypt_patch_available(game.get_id()) else "No"

            # Insert the data into the tree-view
            self.treeview_game_list.insert(parent='', index=count, iid=count, text='',
                                        values=(game_id, game_name, disc_number, number_of_bins, name_valid, bmp_present, cu2_present, lst_present, patch_available))
    # ************************************************************************************


    # ******************************************************
    # GUI functions below
    # ******************************************************

    def _prevent_hidden_files(self):
        """Prevent hidden files in file browser dialog"""
        try:
            try:
                self.window.tk.call('tk_getOpenFile', '-foobarbaz')
            except TclError:
                pass
            self.window.tk.call('set', '::tk::dialog::file::showHiddenBtn', '1')
            self.window.tk.call('set', '::tk::dialog::file::showHiddenVar', '0')
        except Exception:
            pass

    def _on_treeview_click(self, event):
        """Handle left-click events on the Treeview"""
        tree = event.widget
        item = tree.identify_row(event.y)
        if item:
            # Highlight the clicked row
            tree.selection_set(item)

            # Get the game ID
            #values = tree.item(item, "values")
            #game_id = values[0]

            # Find the game object using the game ID
            #the_game = self._find_game_by_id(game_id)

            # Determine the BMP image path from the CUE file path
            #bmp_path = the_game.get_cue_sheet().get_file_path()[:-4] + ".bmp"

            # Display the BMP image
            #self._load_image(bmp_path)

    def _update_progress_bar(self, value):
        """Update the progress bar"""
        self.progress_bar['value'] = value
        if self.window:
            self.window.update()
        sleep(0.1)

    def _update_window(self):
        """Update the main UI window"""
        if self.window:
            self.window.update()
        sleep(0.02)

    def _browse_button_clicked(self):
        """Handle browse button click"""
        selected_path = filedialog.askdirectory(initialdir='/', title='Select Game Directory')
        self.src_path.set(selected_path)
        self.label_src.configure(text= f"  {self.src_path.get()}")
        self._parse_game_list()
        self.button_start['state'] = 'normal'

    def _start_button_clicked(self):
        """Handle start button click"""
        if self.src_path.get():
            self.button_start['state'] = 'disabled'
            self.process_games()
            self.button_start['state'] = 'normal'

    def _checkbox_changed(self):
        """Handle checkbox change"""
        self.redump_rename.set(True if self.redump_rename.get() else False)

    def _get_stored_theme(self):
        """Get stored theme from config"""
        if exists(self.config_file_path):
            with open(self.config_file_path, encoding="utf-8") as config_file:
                return load(config_file)['theme']
        else:
            return "superhero"

    def _store_selected_theme(self, theme_name):
        """Store selected theme"""
        with open(self.config_file_path, mode="w", encoding="utf-8") as config_file:
            config_file.write(dumps({"theme": theme_name}))

    def _switch_theme(self, theme_name):
        """Switch UI theme"""
        style = Style()
        style.theme_use(theme_name)
        self._store_selected_theme(theme_name)


    # ************************************************************************************
    def setup_gui(self):
        """Setup the GUI"""
        window_width = 1000
        window_height = 800

        self.window = Window(title=f'PSIO Game Assistant v{self.CURRENT_REVISION}',
                               themename=self._get_stored_theme(), size=[window_width, window_height], resizable=[False, False])

        # Set the app icon based on OS
        self._load_app_icon()

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
        self._gui_browse_frame(window_width)

        # Game list frame
        self._gui_game_list_frame(window_width)

        # Process frame
        self._gui_process_frame(window_width)

        self._prevent_hidden_files()
    # ************************************************************************************


    # ************************************************************************************
    def _load_app_icon(self):
        """Load the application icon based on the OS"""
        try:
            if sys.platform.lower() == "win32":
                # Use .ico file for Windows
                icon_path = self._resource_path('icon.ico')
                if exists(icon_path):
                    self.window.iconbitmap(icon_path)
            else:
                # Use .png file for macOS/Linux
                icon_path = self._resource_path('icon.png')
                if exists(icon_path):
                    self.icon = PhotoImage(file=icon_path)
                    self.window.iconphoto(True, self.icon)

        except TclError as error:
            self._debug_print(f"Error setting icon: {error}")
    # ************************************************************************************


    # ************************************************************************************
    def _gui_browse_frame(self, window_width: int):
        """Create the browse frame"""
        browse_frame = Labelframe(self.window, text='Root Directory', bootstyle="primary")
        browse_frame.place(x=15, y=10, width=window_width -30, height=70)

        self.label_src = Label(self.window, text=self.src_path.get(), width=60, borderwidth=2, relief='solid', bootstyle="primary", font=("Arial", 11))
        self.label_src.place(x=30, y=35, width=window_width -200, height=30)

        button_src_browse = Button(self.window, text='Browse', bootstyle="primary", command=self._browse_button_clicked)
        button_src_browse.place(x=840, y=35, width=window_width -870, height=30)
    # ************************************************************************************


    # ************************************************************************************
    def _gui_game_list_frame(self, window_width: int):
        """Create the game list frame"""
        game_list_frame = Labelframe(self.window, text='Games', bootstyle="primary")
        game_list_frame.place(x=15, y=100, width=window_width -30, height=450)

        self.treeview_game_list = Treeview(self.window, bootstyle='primary')
        self.treeview_game_list.bind("<Button-1>", self._on_treeview_click)

        self.treeview_game_list['columns'] = ('ID', 'Name', 'Disc', 'Bin Files', 'Name Valid', 'BMP', 'CU2', 'LST', 'LibCrypt')
        self.treeview_game_list.column('#0', width=0, stretch=NO)
        self.treeview_game_list.column('ID', anchor=CENTER, width=75)
        self.treeview_game_list.column('Name', anchor=CENTER, width=330)
        self.treeview_game_list.column('Disc', anchor=CENTER, width=60)
        self.treeview_game_list.column('Bin Files', anchor=CENTER, width=60)
        self.treeview_game_list.column('Name Valid', anchor=CENTER, width=75)
        self.treeview_game_list.column('BMP', anchor=CENTER, width=40)
        self.treeview_game_list.column('CU2', anchor=CENTER, width=40)
        self.treeview_game_list.column('LST', anchor=CENTER, width=40)
        self.treeview_game_list.column('LibCrypt', anchor=CENTER, width=40)

        self.treeview_game_list.heading('#0', text='', anchor=CENTER)
        self.treeview_game_list.heading('ID', text='ID', anchor=CENTER)
        self.treeview_game_list.heading('Name', text='Name', anchor=CENTER)
        self.treeview_game_list.heading('Disc', text='Disc', anchor=CENTER)
        self.treeview_game_list.heading('Bin Files', text='Bin Files', anchor=CENTER)
        self.treeview_game_list.heading('Name Valid', text='Name Valid', anchor=CENTER)
        self.treeview_game_list.heading('BMP', text='BMP', anchor=CENTER)
        self.treeview_game_list.heading('CU2', text='CU2', anchor=CENTER)
        self.treeview_game_list.heading('LST', text='LST', anchor=CENTER)
        self.treeview_game_list.heading('LibCrypt', text='LibCrypt', anchor=CENTER)

        scrollbar_game_list = Scrollbar(self.window, bootstyle="primary-round", orient=VERTICAL, 
                                      command=self.treeview_game_list.yview)

        self.treeview_game_list.configure(yscroll=scrollbar_game_list.set)
        self.treeview_game_list.place(x=30, y=120, width=window_width -70, height=410)
        scrollbar_game_list.place(x=960, y=120, height=410)
    # ************************************************************************************


    # ************************************************************************************
    def _gui_process_frame(self, window_width: int):
        """Create the process frame"""
        frame_y = 580

        progress_frame = Labelframe(self.window, text='Process', bootstyle="primary")
        progress_frame.place(x=20, y=frame_y, width=window_width -30, height=190)

        self.progress_bar = Floodgauge(font=(None, 14, 'bold'), mask='', mode='determinate')
        self.progress_bar.place(x=30, y=frame_y +30, width=window_width -50, height=30)

        self.label_progress = Label(self.window, text="", width=120, bootstyle="primary")
        self.label_progress.place(x=30, y=frame_y +60, width=window_width -450, height=30)

        Checkbutton(self.window, text='Redump Rename', bootstyle="primary", takefocus=0,
                   variable=self.redump_rename, command=self._checkbox_changed).place(x=30, y=frame_y +110)

        self.button_start = Button(self.window, text='Process', command=self._start_button_clicked, state=DISABLED)
        self.button_start.place(x=30, y=frame_y +140, width=window_width -50, height=30)

        self.label_progress.after(1000, ensure_database_exists)
    # ************************************************************************************


    def run(self):
        """Run the application"""
        self.setup_gui()
        self.window.mainloop()


def parse_arguments():
    """Parse command-line arguments"""
    parser = ArgumentParser(
        description="PSIO Game Assistant for preparing PlayStation games for use with a PSIO device."
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug mode for verbose output."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    app = PSIOGameAssistant(args)
    app.run()
