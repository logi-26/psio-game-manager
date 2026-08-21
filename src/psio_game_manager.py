#!/usr/bin/env python3
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
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

'''
PSIO Game Manager

This is an open-source application for preparing PlayStation games for use with a PSIO device

Features:
* Runs in batch mode, processing all of the games that have been selected
* Performs CRC checks of all tracks in the bin files
* Merge any games that have multiple bin files into a single bin file
* Update the cue sheet file to only contain a single bin file
* Detect games that use CCDA audio and generate a cu2 file
* Fix any game names that are too long or contain invalid characters
* Add a bmp image file for each game in the correct resolution for the PSIO menu
* Detect multi-disc games and organise them into a single directory and generate a multi-disc lst file
* Patch LibCrypt games

Optional:
Rename all games using the game names from the PlayStation Redump project

Usage:
Place your PlayStation games into sub-directories that each contains the bin/cue files for the game
Point the application at the folder root directory and it will detect the games in the sub-directories

For best performance, process your games on a computers HDD/SSD and then transfer to SD afterwards
Read/write speeds to and SD card are a lot slower and it can take a long time if you have lots of multi-bin games

Copyright (C) 2021 LoGi26
'''


# System imports
import sys
import threading
import webbrowser
import urllib.request
from datetime import datetime
from os.path import exists, join, dirname, abspath
from json import load, loads, dumps
from argparse import ArgumentParser
from ast import literal_eval
from tkinter import Menu, filedialog, StringVar, BooleanVar, TclError, PhotoImage, NO, CENTER, VERTICAL
from ttkbootstrap import Window, Toplevel, Floodgauge, Treeview, Style, Scrollbar, Labelframe, Label, Button
from ttkbootstrap.dialogs import MessageDialog
from ttkbootstrap.constants import DISABLED
from pathlib2 import Path

# Local classes
from game_files import Game, Cuesheet, Binfile
from utils import Utils
from db import GameDatabase
from binmerge import BinMerger
from cu2 import Cu2Generator
from ppf_patcher import PPFProcessor
from crc_32 import CrcFileVerifier


class PSIOGameManager:
    CURRENT_REVISION = 1.0
    MAX_GAME_NAME_LENGTH = 56

    def __init__(self, args=None):
        """Initialise the PSIO Game Manager application"""

        self.game_list = []
        self.script_root_dir = Path(abspath(dirname(sys.argv[0])))
        self.covers_path = join(dirname(self.script_root_dir), 'covers')
        self.error_log_file = join(dirname(self.script_root_dir), 'errors.txt')
        self.config_file_path = join(self.script_root_dir, 'config')

        # Set debug mode based on the parsed command-line arguments
        self.debug_mode = args.debug if args else False

        # Initialise the local classes
        self.db = GameDatabase(debug_mode=self.debug_mode)
        self.crc_verifier = CrcFileVerifier(debug_mode=self.debug_mode)
        self.bin_merger = BinMerger(debug_mode=self.debug_mode)
        self.ppf_patcher = PPFProcessor(debug_mode=self.debug_mode)
        self.cu2_generator = Cu2Generator(debug_mode=self.debug_mode)

        # Set the database paths
        self.database_name = "psio_assist.db"
        self.database_path = self._resource_path("data")
        self.db.set_database_path(self.database_path, self.database_name)

        self.utils = Utils(database=self.db, debug_mode=self.debug_mode)

        # Set the icon path
        self.icon_path = self._resource_path("icon.ico")

        # Initialise variables
        self.args = args
        self.window = None
        self.icon = None
        self.src_path = None
        self.dest_path = None
        self.redump_rename = None

        # GUI elements
        self.progress_bar = None
        self.button_start = None
        self.button_browse = None
        self.button_cancel = None
        self.treeview_game_list = None
        self.label_src = None
        self.cover_art_frame = None
        self.summary_labels = {}
        self.selected_theme_var = None

        self._cancel_event = threading.Event()

        self._debug_print(f'\nPSIO Game Manager v{self.CURRENT_REVISION}')


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
    def _set_progress_text(self, message: str):
        """Set the text inside the progress bar"""
        safe = message.replace('{', '{{').replace('}', '}}')
        self.window.after(0, lambda: self.progress_bar.configure(mask=safe))
    # ************************************************************************************


    # ************************************************************************************
    def process_games(self):
        """Process the games in the game list"""

        self._debug_print('\nPROCESSING GAMES...')

        # Loop through all of the Game objects in the game list
        for game_index, game in enumerate(self.game_list):

            if self._cancel_event.is_set():
                break

            # Display the game name in the progress label
            game_name = game.get_cue_sheet().get_game_name()
            self._set_progress_text(f"Processing - {game_name}")
            self._update_progress_bar(0)

            self._debug_print('\n***********************************************************')
            self._debug_print(f'GAME_ID: {game.get_id()}')
            self._debug_print(f'GAME_NAME: {game_name}')

            # Merge multi-bin files
            self._merge_multi_bin_files(game)
            self._update_progress_bar(30)

            # Generate CU2 file for games with CCDA audio
            self._generate_cu2_file(game)
            self._update_progress_bar(40)

            # Rename the game using the game name from the Redump project
            if self.redump_rename.get():
                self.utils.rename_game_using_redump(game)
            self._update_progress_bar(50)

            # Validate the game name
            self.utils.validate_game_name(game)
            self._update_progress_bar(65)

            # Add the game cover art
            self.utils.add_game_cover_art(game)
            self._update_progress_bar(75)

            # Apply LibCrypt PPF patch
            self.utils.apply_libcrypt_patch(game)
            self._update_progress_bar(95)

            # Schedule the row update on the main thread
            self.window.after(0, lambda idx=game_index: self._update_game_row(idx))

            self._debug_print('***********************************************************\n')

        if self._cancel_event.is_set():
            self._set_progress_text("Cancelled")
            self._update_progress_bar(0)
            self.window.after(0, self._display_game_list)
            self._debug_print('Processing cancelled.\n')
            return

        # Generate multi-disc games after all of the other processes have been completed
        self._update_progress_bar(100)
        self._set_progress_text("Generating multi-disc files...")
        self.utils.generate_multidisc_files(self.game_list)

        # Clear the progress status
        self._update_progress_bar(100)
        self._set_progress_text("")

        # Rebuild the full game list on the main thread once all processing is done
        self.window.after(0, self._display_game_list)

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
            self._set_progress_text(f"Merging bin files - {game_name}")
            self.utils.merge_bin_files(game)

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
            self._set_progress_text(f"Generating cu2 file - {game_name}")

            # Generate the CU2 file
            cu2_generated = self.cu2_generator.generate_cu2(cue_full_path, f'{game_name}.bin')

            if cu2_generated:
                game.set_cu2_present(True)
    # ************************************************************************************


    # ************************************************************************************
    def _sort_game_list(self):
        """Sort the game list alphabetically by game name."""
        self.game_list.sort(key=lambda game: game.get_cue_sheet().get_game_name(), reverse=False)
    # ************************************************************************************


    # ************************************************************************************
    def _create_game_from_cue(self, game_directory_path: str, cue_sheet: str, sub_folder: str, selected_path: str) -> Game:
        """Create a Game object from a CUE sheet."""
        cue_sheet_path = join(game_directory_path, cue_sheet)

        #self._set_progress_text(f"Parsing Game: {str(Path(game_directory_path))}")
        self._set_progress_text(f"Parsing Game: {str(Path(game_directory_path).stem)}")

        # Check for cover art
        cover_art_path = join(game_directory_path, cue_sheet[:-3])
        cover_art_present = exists(f'{cover_art_path}bmp') or exists(f'{cover_art_path}BMP')
        self._update_progress_bar(20)

        # Check for multi-disc and CU2 files
        multi_disc_file_present = exists(join(game_directory_path, 'MULTIDISC.LST'))
        cu2_present = exists(join(game_directory_path, f'{cue_sheet[:-3]}cu2'))
        cu2_required = self.utils.detect_cdda(cue_sheet_path)
        self._update_progress_bar(30)

        # Parse the BIN files and Tracks from the CUE file
        bin_files = self.utils.parse_cue_file(cue_sheet_path)
        self._update_progress_bar(40)

        # Get the game details from the BIN files
        game_id = self.utils.parse_game_id(bin_files[0].get_file_path()) if bin_files else None
        self._update_progress_bar(50)

        game_name = Path(bin_files[0].get_file_name()).stem
        game_data = self.db.get_game_data(game_id) if game_id else {}
        disc_number = game_data.get('disc_number', 0)
        disc_collection = game_data.get('collection', [])
        libcrypt_required = game_data.get('libcrypt', False)
        self._update_progress_bar(60)

        # Convert the disc collection string into a list
        if disc_collection:
            disc_collection = literal_eval(disc_collection)

        self._update_progress_bar(70)

        # Create Cuesheet object
        the_cue_sheet = Cuesheet(cue_sheet, cue_sheet_path, game_name)

        # Add the BIN files to the Cuesheet object
        for bin_file in bin_files:
            the_cue_sheet.add_bin_file(bin_file)

        self._update_progress_bar(80)

        # Create the Game object
        the_game =  Game(
            sub_folder, selected_path, game_id, disc_number, disc_collection,
            the_cue_sheet, cover_art_present, cu2_present, cu2_required,
            multi_disc_file_present, libcrypt_required
        )

        # Check if a LibCrypt patch has already been applied to the BIN file
        self.utils.libcrypt_already_applied(the_game)

        # Perform CRC-32 check on each BIN file from the Game
        if self.crc_check.get():
            crc_valid = self.utils.crc_check_bin(the_game)
            the_game.set_crc_valid(crc_valid)
            
        self._update_progress_bar(90)

        # Return the Game object
        self._update_progress_bar(100)
        return the_game
    # ************************************************************************************


    # ************************************************************************************
    def _process_sub_folder(self, selected_path: str, sub_folder: str):
        """Process a single sub-folder to extract game information and add to game list."""
        game_directory_path = join(selected_path, sub_folder)
        cue_sheets = self.utils.find_cue_sheets(game_directory_path)

        for cue_sheet in cue_sheets:
            # Create the Game object
            game = self._create_game_from_cue(game_directory_path, cue_sheet, sub_folder, selected_path)
            if game:
                # Add the Game to the game list
                self.game_list.append(game)
                self._print_game_details(game)

                # Append just this row rather than rebuilding the entire list
                self._append_game_row(game)
    # ************************************************************************************


    # ************************************************************************************
    def _create_game_list(self, selected_path: str):
        """Create and populate the global game list."""
        self.game_list = []
        sub_folders = self.utils.get_sub_folders(selected_path)

        self._debug_print('\nGAME DETAILS:\n')
        self._set_progress_text("Generating game list...")

        if not sub_folders:
            return

        for sub_folder in sub_folders:
            if self._cancel_event.is_set():
                break
            self._process_sub_folder(selected_path, sub_folder)

        self._sort_game_list()
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

        self._set_progress_text("Generating Game List...")

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
            if self.utils.is_multi_disc(game):
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

        self._set_progress_text("")
        self._update_progress_bar(100)

        self.window.after(0, lambda: self.button_cancel.configure(state='disabled'))
        self.window.after(0, lambda: self.button_browse.configure(state='normal'))

        if self._cancel_event.is_set():
            self._set_progress_text("Cancelled")
            self.window.after(0, self._display_game_list)
            return

        if self.debug_mode:
            self.window.after(0, lambda m=message: MessageDialog(
                m, title='Game Details', width=650, padding=(20, 20)
            ).show())

        self.window.after(0, self._display_game_list)
        self.window.after(0, lambda: self.button_start.configure(state='normal'))
    # ************************************************************************************


    # ************************************************************************************
    def _update_game_row(self, game_index):
        """Update a single row in the Treeview for the game at the given index"""
        if not 0 <= game_index < len(self.game_list):
            self._debug_print(f"Invalid game index: {game_index}")
            return

        # Get the game object
        game = self.game_list[game_index]
        bools = ('No', 'Yes')

        # Compute the updated values for the row (same logic as _display_game_list)
        game_id = game.get_id()
        game_name = game.get_cue_sheet().get_game_name()
        disc_number = game.get_disc_number()
        number_of_bins = len(game.get_cue_sheet().get_bin_files())
        name_valid = bools[len(game_name) <= self.MAX_GAME_NAME_LENGTH and '.' not in game_name]
        cu2_present = bools[game.get_cu2_present()] if game.get_cu2_required() else "*"

        # Check if the game is a multi-disc game and if an LST file is available
        lst_present = "*"
        if game.get_disc_number() > 0:
            lst_present = "Yes" if game.get_multi_disc_file_present() else "No"

        # Check if the cover art is available
        bmp_present = bools[game.get_cover_art_present()]

        # Check if the game uses LibCrypt encryption and if a patch has already been applied
        libcrypt_patch = "*"
        if game.get_libcrypt_required():
            libcrypt_patch = "Yes" if game.get_libcrypt_applied() else "No"

        # Check if the CRC-32 matches the data from the PlayStation Redump project
        crc_32 = "*" if not self.crc_check.get() else "Yes" if game.get_crc_valid() else "No"

        # Update the existing row in the Treeview
        try:
            self.treeview_game_list.item(game_index, values=(game_id, game_name, disc_number, number_of_bins, crc_32, name_valid, bmp_present, cu2_present, lst_present, libcrypt_patch))

            # Scroll to the updated item
            self.treeview_game_list.see(game_index)
            # Highlight the updated row
            self.treeview_game_list.selection_set(game_index)
        except TclError as e:
            self._debug_print(f"Error updating Treeview row {game_index}: {e}")
    # ************************************************************************************


    # ************************************************************************************
    def _append_game_row(self, game: Game):
        """Insert one game row at the bottom of the Treeview without rebuilding the whole list."""
        bools = ('No', 'Yes')
        game_id = game.get_id()
        game_name = game.get_cue_sheet().get_game_name()
        disc_number = game.get_disc_number()
        number_of_bins = len(game.get_cue_sheet().get_bin_files())
        name_valid = bools[len(game_name) <= self.MAX_GAME_NAME_LENGTH and '.' not in game_name]
        cu2_present = bools[game.get_cu2_present()] if game.get_cu2_required() else "*"
        lst_present = ("Yes" if game.get_multi_disc_file_present() else "No") if disc_number > 0 else "*"
        bmp_present = bools[game.get_cover_art_present()]
        libcrypt_patch = ("Yes" if game.get_libcrypt_applied() else "No") if game.get_libcrypt_required() else "*"
        crc_32 = "Yes" if game.get_crc_valid() else "No" if self.crc_check.get() else "*"
        values = (game_id, game_name, disc_number, number_of_bins, crc_32, name_valid,
                  bmp_present, cu2_present, lst_present, libcrypt_patch)
        iid = len(self.game_list) - 1

        def _insert():
            self.treeview_game_list.insert(parent='', index='end', iid=iid, text='', values=values)
            self.treeview_game_list.yview_moveto(1)
            self.treeview_game_list.selection_set(iid)

        self.window.after(0, _insert)
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
            name_valid = bools[len(game_name) <= self.MAX_GAME_NAME_LENGTH and '.' not in game_name]
            cu2_present = bools[game.get_cu2_present()] if game.get_cu2_required() else "*"

            # Check if the games is a multi-disc game and if an LST file is available
            lst_present = "*"
            if game.get_disc_number() > 0:
                lst_present = "Yes" if game.get_multi_disc_file_present() else "No"

            # Check if the cover art is available
            bmp_present = bools[game.get_cover_art_present()]

            # Check if the game uses LibCrypt encryption and if a patch has already been applied
            libcrypt_patch = "*"
            if game.get_libcrypt_required():
                libcrypt_patch = "Yes" if game.get_libcrypt_applied() else "No"

            # Check if the CRC-32 matches the data from the PlayStation Redump project
            if self.crc_check.get():
                crc_32 = "Yes" if game.get_crc_valid() else "No"
            else:
                crc_32 = "*"

            # Insert the data into the tree-view
            self.treeview_game_list.insert(parent='', index=count, iid=count, text='',
                                        values=(game_id, game_name, disc_number, number_of_bins, crc_32, name_valid, bmp_present, cu2_present, lst_present, libcrypt_patch))

            # Autoscroll to the last item if the list is not empty
            if self.game_list:
                self.treeview_game_list.yview_moveto(1)

                # Highlight the updated row
                self.treeview_game_list.selection_set(count)

        self._update_summary()
    # ************************************************************************************


    # ************************************************************************************
    def _print_game_details(self, game: Game):
        """Print Game details for debugging"""
        self._debug_print("\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        game_path = join(game.get_directory_path(), game.get_directory_name())
        self._debug_print(f'Game ID: {game.get_id()}')
        self._debug_print(f'Game Name: {game.get_cue_sheet().get_game_name()}')
        self._debug_print(f'Game Path: {game_path}')
        self._debug_print(f'Disc Number: {game.get_disc_number()}')
        self._debug_print(f'Number of Bin Files: {len(game.get_cue_sheet().get_bin_files())}')
        if game.get_disc_collection():
            self._debug_print(f'Disc Collection: {game.get_disc_collection()}')
        self._debug_print(f'Has Cover ART: {game.get_cover_art_present()}')
        self._debug_print(f'CU2 Required: {game.get_cu2_required()}')
        self._debug_print(f'Has CU2: {game.get_cu2_present()}')
        self._debug_print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
    # ************************************************************************************


    # ************************************************************************************
    def _print_bin_file_details(self, bin_files: list[Binfile]):
        """Print BIN file details for debugging"""
        self._debug_print("\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        self._debug_print("BIN FILES:")
        for binfile in bin_files:
            self._debug_print("++++++++++++++++++++++++++++++")
            self._debug_print(f"File: {binfile.get_file_name()}")
            self._debug_print(f"Path: {binfile.get_file_path()}")
            self._debug_print(f"Size: {binfile.get_size()}")

            self._debug_print("\nTRACKS:")
            for track in binfile.get_tracks():
                self._debug_print(f"Track {track.get_track_number()}")
                self._debug_print(f"Type={track.get_track_type()}")
                self._debug_print(f"Sectors={track.get_sectors()}")

                self._debug_print("\nINDEXES:")
                for index in track.get_indexes():
                    self._debug_print(f"Index {index['id']}")
                    self._debug_print(f"Stamp={index['stamp']}")
                    self._debug_print(f"Offset={index['file_offset']}")

            self._debug_print("++++++++++++++++++++++++++++++")
        self._debug_print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
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

    def _update_progress_bar(self, value: int):
        """Update the progress bar"""
        self.window.after(0, lambda: self.progress_bar.configure(value=value))

    def _browse_button_clicked(self):
        """Handle browse button click"""
        selected_path = filedialog.askdirectory(initialdir='/', title='Select Game Directory')
        if not selected_path:
            return
        self.src_path.set(selected_path)
        self.label_src.configure(text=f"  {self.src_path.get()}")
        self.button_start['state'] = 'disabled'
        self.button_browse['state'] = 'disabled'
        self.button_cancel['state'] = 'normal'
        self._cancel_event.clear()
        for item in self.treeview_game_list.get_children():
            self.treeview_game_list.delete(item)
        self._clear_summary()
        self.progress_bar.configure(value=0, mask='')
        threading.Thread(target=self._parse_game_list, daemon=True).start()

    def _start_button_clicked(self):
        """Handle start button click"""
        if self.src_path.get():
            self.button_start['state'] = 'disabled'
            self.button_browse['state'] = 'disabled'
            self.button_cancel['state'] = 'normal'
            self._cancel_event.clear()
            threading.Thread(target=self._run_processing, daemon=True).start()

    def _run_processing(self):
        """Run process_games on a background thread and re-enable the buttons when done."""
        self.process_games()
        self.window.after(0, lambda: self.button_start.configure(state='normal'))
        self.window.after(0, lambda: self.button_browse.configure(state='normal'))
        self.window.after(0, lambda: self.button_cancel.configure(state='disabled'))

    def _cancel_button_clicked(self):
        """Signal the active background operation to stop."""
        self._cancel_event.set()
        self.button_cancel['state'] = 'disabled'
        self._set_progress_text("Cancelling...")

    def _load_config(self) -> dict:
        """Load the full config dict from disk"""
        if exists(self.config_file_path):
            with open(self.config_file_path, encoding="utf-8") as config_file:
                return load(config_file)
        return {}

    def _save_config(self, config: dict):
        """Save the full config dict to disk"""
        with open(self.config_file_path, mode="w", encoding="utf-8") as config_file:
            config_file.write(dumps(config))

    def _get_stored_theme(self):
        """Get stored theme from config"""
        return self._load_config().get('theme', 'everforest-dark')

    def _store_selected_theme(self, theme_name):
        """Store selected theme"""
        config = self._load_config()
        config['theme'] = theme_name
        self._save_config(config)

    def _switch_theme(self, theme_name):
        """Switch UI theme"""
        style = Style()
        style.theme_use(theme_name)
        self._store_selected_theme(theme_name)

    def _toggle_check_update(self):
        """Persist the check update on startup preference"""
        config = self._load_config()
        config['check_update'] = self.check_update_on_startup.get()
        self._save_config(config)


    # ************************************************************************************
    def _check_for_update(self):
        """Check GitHub for a newer release and notify the user if one is available"""
        try:
            url = 'https://api.github.com/repos/logi-26/psio-game-manager/releases/latest'
            req = urllib.request.Request(url, headers={'User-Agent': 'psio-game-manager'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = loads(response.read())

            latest_tag = data.get('tag_name', '').lstrip('v')
            if not latest_tag:
                return

            current = tuple(int(x) for x in str(self.CURRENT_REVISION).split('.'))
            latest = tuple(int(x) for x in latest_tag.split('.'))

            if latest > current:
                self.window.after(0, lambda: self._show_update_dialog(latest_tag))
        except Exception:
            pass
    # ************************************************************************************


    # ************************************************************************************
    def _show_update_dialog(self, latest_version: str):
        """Show a dialog informing the user that a new version is available"""
        dialog = Toplevel(self.window)
        dialog.title('Update Available')
        dialog.resizable(False, False)
        dialog.grab_set()

        try:
            if sys.platform.lower() == "win32":
                icon_path = self._resource_path('icon.ico')
                if exists(icon_path):
                    dialog.iconbitmap(icon_path)
            elif self.icon:
                dialog.iconphoto(True, self.icon)
        except TclError:
            pass

        pw, ph = self.window.winfo_width(), self.window.winfo_height()
        px, py = self.window.winfo_x(), self.window.winfo_y()
        dw, dh = 360, 160
        dialog.geometry(f'{dw}x{dh}+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}')

        Label(dialog, text='Update Available',
              font=('Arial', 14, 'bold'), bootstyle='primary').pack(pady=(24, 8))
        Label(dialog, text=f'Version {latest_version} is available (current: {self.CURRENT_REVISION})',
              font=('Arial', 9)).pack(pady=(0, 16))

        btn_frame = Labelframe(dialog, bootstyle='default')
        btn_frame.pack()
        Button(btn_frame, text='View on GitHub',
               bootstyle='primary', width=14,
               command=lambda: (webbrowser.open('https://github.com/logi-26/psio-game-manager/releases'), dialog.destroy())).pack(side='left', padx=(0, 8))
        Button(btn_frame, text='Dismiss',
               bootstyle='secondary', width=10,
               command=dialog.destroy).pack(side='left')
    # ************************************************************************************


    # ************************************************************************************
    def _show_about_dialog(self):
        """Show the About dialog"""
        dialog = Toplevel(self.window)
        dialog.title('About')
        dialog.resizable(False, False)
        dialog.grab_set()

        # Apply the same icon as the main window
        try:
            if sys.platform.lower() == "win32":
                icon_path = self._resource_path('icon.ico')
                if exists(icon_path):
                    dialog.iconbitmap(icon_path)
            elif self.icon:
                dialog.iconphoto(True, self.icon)
        except TclError:
            pass

        # Centre over the parent window
        dialog.update_idletasks()
        pw, ph = self.window.winfo_width(), self.window.winfo_height()
        px, py = self.window.winfo_x(), self.window.winfo_y()
        dw, dh = 420, 280
        dialog.geometry(f'{dw}x{dh}+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}')

        Label(dialog, text='PSIO Game Manager',
              font=('Arial', 18, 'bold'), bootstyle='primary').pack(pady=(30, 4))
        Label(dialog, text=f'Version {self.CURRENT_REVISION}',
              font=('Arial', 12)).pack(pady=(0, 4))
        Label(dialog, text=f'Last updated: {datetime.now().strftime("%B %Y")}',
              font=('Arial', 9)).pack(pady=(0, 16))
        Label(dialog,
              text='An open-source tool for preparing PlayStation\ngames for use with a PSIO device.',
              font=('Arial', 10), justify=CENTER).pack(pady=(0, 16))
        Label(dialog, text='Copyright © 2021 LoGi26',
              font=('Arial', 9)).pack(pady=(0, 4))
        Label(dialog, text='Licensed under the GNU General Public License v3',
              font=('Arial', 9)).pack(pady=(0, 20))
        Button(dialog, text='Close', command=dialog.destroy,
               bootstyle='primary', width=12).pack()
    # ************************************************************************************


    # ************************************************************************************
    def setup_gui(self):
        """Setup the GUI"""
        window_width = 1300
        window_height = 850

        try:
            self.window = Window(
                title=f'PSIO Game Manager v{self.CURRENT_REVISION}',
                themename=self._get_stored_theme(),
                size=[window_width, window_height],
                resizable=[False, False]
            )
        except Exception:
            self.window = Window(
                title=f'PSIO Game Manager v{self.CURRENT_REVISION}',
                themename='everforest-dark',
                size=[window_width, window_height],
                resizable=[False, False]
            )

        # Set the app icon based on OS
        self._load_app_icon()

        # Initialise Tkinter variables
        self.src_path = StringVar(self.window)
        self.dest_path = StringVar(self.window)
        self.redump_rename = BooleanVar(self.window)
        self.crc_check = BooleanVar(self.window)

        # Set default checkbox values
        self.redump_rename.set(True)
        self.crc_check.set(False)
        self.check_update_on_startup = BooleanVar(self.window)
        self.check_update_on_startup.set(self._load_config().get('check_update', True))
        self.selected_theme_var = StringVar(self.window, value=self._get_stored_theme())

        # Menu setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Menu > Colour Themes + Exit
        main_menu = Menu(menubar, tearoff=0)
        sub_menu = Menu(main_menu, tearoff=0)
        dark_menu = Menu(sub_menu, tearoff=0)
        light_menu = Menu(sub_menu, tearoff=0)
        all_themes = sorted(Style().theme_names())
        dark_themes = [t for t in all_themes if t.endswith('-dark')]
        light_themes = [t for t in all_themes if t.endswith('-light')]
        for theme in dark_themes:
            dark_menu.add_checkbutton(
                label=theme.removesuffix('-dark'),
                variable=self.selected_theme_var,
                onvalue=theme,
                offvalue='',
                command=lambda t=theme: (self.selected_theme_var.set(t), self._switch_theme(t))
            )
        for theme in light_themes:
            light_menu.add_checkbutton(
                label=theme.removesuffix('-light'),
                variable=self.selected_theme_var,
                onvalue=theme,
                offvalue='',
                command=lambda t=theme: (self.selected_theme_var.set(t), self._switch_theme(t))
            )
        sub_menu.add_cascade(label='Dark', menu=dark_menu)
        sub_menu.add_cascade(label='Light', menu=light_menu)
        main_menu.add_command(label='About', command=self._show_about_dialog)
        main_menu.add_checkbutton(label='Check for Update on Startup',
                                  variable=self.check_update_on_startup,
                                  command=self._toggle_check_update,
                                  onvalue=True, offvalue=False)
        main_menu.add_separator()
        main_menu.add_cascade(label="Color Themes", menu=sub_menu)
        main_menu.add_separator()
        main_menu.add_command(label='Report Bug', command=lambda: webbrowser.open('https://github.com/logi-26/psio-game-manager/issues'))
        main_menu.add_separator()
        main_menu.add_command(label='Exit', command=self.window.destroy)
        menubar.add_cascade(label="Menu", menu=main_menu)

        # Options > Auto Rename + CRC Check
        file_menu = Menu(menubar, tearoff=0)

        def toggle_redump_rename():
            self._debug_print(f"Auto Rename is now: {self.redump_rename.get()}")

        file_menu.add_checkbutton(
            label="Auto Rename",
            variable=self.redump_rename,
            command=toggle_redump_rename,
            onvalue=True,
            offvalue=False
        )

        file_menu.add_separator()

        def toggle_crc_check():
            self._debug_print(f"CRC Check is now: {self.crc_check.get()}")

        file_menu.add_checkbutton(
            label="CRC Check",
            variable=self.crc_check,
            command=toggle_crc_check,
            onvalue=True,
            offvalue=False
        )

        menubar.add_cascade(label="Game Options", menu=file_menu, underline=0)

        # Browse frame
        self._gui_browse_frame(window_width)

        # Game list frame
        self._gui_game_list_frame(window_width)

        # Summary frame
        self._gui_summary_frame(window_width)

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

        self.button_browse = Button(self.window, text='Browse', bootstyle="primary", command=self._browse_button_clicked)
        self.button_browse.place(x=window_width - 155, y=35, width=130, height=30)
    # ************************************************************************************


    # ************************************************************************************
    def _gui_game_list_frame(self, window_width: int):
        """Create the game list frame"""
        game_list_frame = Labelframe(self.window, text='Games', bootstyle="primary")
        game_list_frame.place(x=15, y=100, width=window_width -30, height=450)

        # Create a custom style for the Treeview
        style = Style()
        style.configure("Custom.Treeview", font=("Arial", 10))
        style.configure("Custom.Treeview.Heading", font=("Arial", 10, "bold"))

        self.treeview_game_list = Treeview(self.window, style="Custom.Treeview", bootstyle='primary')
        self.treeview_game_list.bind("<Button-1>", self._on_treeview_click)

        self.treeview_game_list['columns'] = ('ID', 'Name', 'Disc', 'Bin Files', 'CRC Valid', 'Name Valid', 'BMP', 'CU2', 'LST', 'LibCrypt')
        self.treeview_game_list.column('#0', width=0, stretch=NO)
        self.treeview_game_list.column('ID', anchor=CENTER, width=75)
        self.treeview_game_list.column('Name', anchor=CENTER, width=400)
        self.treeview_game_list.column('Disc', anchor=CENTER, width=60)
        self.treeview_game_list.column('Bin Files', anchor=CENTER, width=60)
        self.treeview_game_list.column('CRC Valid', anchor=CENTER, width=45)
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
        self.treeview_game_list.heading('CRC Valid', text='CRC Valid', anchor=CENTER)
        self.treeview_game_list.heading('Name Valid', text='Name Valid', anchor=CENTER)
        self.treeview_game_list.heading('BMP', text='BMP', anchor=CENTER)
        self.treeview_game_list.heading('CU2', text='CU2', anchor=CENTER)
        self.treeview_game_list.heading('LST', text='LST', anchor=CENTER)
        self.treeview_game_list.heading('LibCrypt', text='LibCrypt', anchor=CENTER)

        scrollbar_game_list = Scrollbar(self.window, bootstyle="primary-round", orient=VERTICAL,
                                      command=self.treeview_game_list.yview)

        self.treeview_game_list.configure(yscroll=scrollbar_game_list.set)
        self.treeview_game_list.place(x=30, y=120, width=window_width -70, height=410)
        scrollbar_game_list.place(x=window_width - 35, y=120, height=410)
    # ************************************************************************************


    # ************************************************************************************
    def _gui_summary_frame(self, window_width: int):
        """Create the summary frame"""
        summary_frame = Labelframe(self.window, text='Summary', bootstyle="primary")
        summary_frame.place(x=15, y=560, width=window_width - 30, height=80)

        stats = ['Total', 'Unidentified', 'Invalid Names', 'Missing Covers', 'Multi-bin', 'Multi-disc']

        for i, stat in enumerate(stats):
            summary_frame.columnconfigure(i, weight=1)
            Label(summary_frame, text=stat, font=('Arial', 9), bootstyle='primary').grid(row=0, column=i, pady=(5, 0))
            val_label = Label(summary_frame, text='-', font=('Arial', 14, 'bold'))
            val_label.grid(row=1, column=i, pady=(0, 5))
            self.summary_labels[stat] = val_label
    # ************************************************************************************


    # ************************************************************************************
    def _compute_summary(self) -> dict:
        """Compute summary statistics from the current game list"""
        total = len(self.game_list)
        unidentified = sum(1 for g in self.game_list if g.get_id() is None)
        no_cover = sum(1 for g in self.game_list if not g.get_cover_art_present() and g.get_disc_number() in (0, 1))
        multi_bin = sum(1 for g in self.game_list if len(g.get_cue_sheet().get_bin_files()) > 1)
        invalid_names = sum(1 for g in self.game_list if len(g.get_cue_sheet().get_game_name()) > self.MAX_GAME_NAME_LENGTH or '.' in g.get_cue_sheet().get_game_name())
        multi_disc = sum(1 for g in self.game_list if g.get_disc_number() == 1)
        return {'Total': total, 'Unidentified': unidentified, 'Missing Covers': no_cover,
                'Multi-bin': multi_bin, 'Invalid Names': invalid_names, 'Multi-disc': multi_disc}
    # ************************************************************************************


    # ************************************************************************************
    def _update_summary(self):
        """Update the summary panel labels with current game list stats"""
        stats = self._compute_summary()
        for key, label in self.summary_labels.items():
            label.configure(text=str(stats[key]))

    def _clear_summary(self):
        """Reset all summary labels to the default placeholder"""
        for label in self.summary_labels.values():
            label.configure(text='-')
    # ************************************************************************************


    # ************************************************************************************
    def _gui_process_frame(self, window_width: int):
        """Create the process frame"""
        frame_y = 650

        progress_frame = Labelframe(self.window, text='Process', bootstyle="primary")
        progress_frame.place(x=20, y=frame_y, width=window_width -30, height=155)

        self.progress_bar = Floodgauge(font=(None, 14, 'bold'), mask='', mode='determinate')
        self.progress_bar.place(x=30, y=frame_y +25, width=window_width -50, height=28)

        self.button_start = Button(self.window, text='Process', command=self._start_button_clicked, state=DISABLED)
        self.button_start.place(x=30, y=frame_y +75, width=window_width -50, height=30)

        self.button_cancel = Button(self.window, text='Cancel', bootstyle='danger',
                                    command=self._cancel_button_clicked, state=DISABLED)
        self.button_cancel.place(x=30, y=frame_y +110, width=window_width -50, height=30)

        self.window.after(1000, self.db.ensure_database_exists)
    # ************************************************************************************


    def run(self):
        """Run the application"""
        self.setup_gui()
        if self.check_update_on_startup.get():
            threading.Thread(target=self._check_for_update, daemon=True).start()
        self.window.mainloop()
        self.db.close()


def parse_arguments():
    """Parse command-line arguments"""
    parser = ArgumentParser(
        description="PSIO Game Manager for preparing PlayStation games for use with a PSIO device."
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug mode for verbose output."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    app = PSIOGameManager(args)
    app.run()
