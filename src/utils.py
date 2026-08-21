# System imports
import subprocess
import zipfile
from os import listdir, scandir, makedirs, remove, access, R_OK
from os.path import exists, join, dirname, splitext, isfile, isabs
from PIL import Image
from re import search, sub
from shutil import copyfile, move, rmtree, which
from typing import Optional
from pathlib2 import Path

try:
    import py7zr
    _PY7ZR_AVAILABLE = True
except ImportError:
    _PY7ZR_AVAILABLE = False

try:
    import rarfile
    _RARFILE_AVAILABLE = True
except ImportError:
    _RARFILE_AVAILABLE = False

def _find_7zip() -> Optional[str]:
    found = which('7z') or which('7za')
    if found:
        return found
    # Fallback for Windows where 7-Zip is installed but not added to PATH
    for path in (r'C:\Program Files\7-Zip\7z.exe', r'C:\Program Files (x86)\7-Zip\7z.exe'):
        if isfile(path):
            return path
    return None

_7ZIP_EXE: Optional[str] = _find_7zip()

# Local imports
from game_files import Game, Binfile, Track
from crc_32 import CrcFileVerifier
from binmerge import BinMerger
from ppf_patcher import PPFProcessor
from helpers import timecode_to_sectors


class Utils:
    """General utilities class"""
    MAX_GAME_NAME_LENGTH = 56
    INVALID_FILENAME_CHARS = r'[.\\/:*?"<>|]'
    COVER_ART_SIZE = (128, 128)
    REGION_CODES = ['DTLS_', 'SCES_', 'SLES_', 'SLED_', 'SCED_', 'SCUS_',
                    'SLUS_', 'SLPS_', 'SCAJ_', 'SLKA_', 'SLPM_', 'SCPS_',
                    'SCPM_', 'PCPX_', 'PAPX_', 'PTPX_', 'LSP0_', 'LSP1_',
                    'LSP2_', 'LSP9_', 'SIPS_', 'ESPM_', 'SCZS_', 'SPUS_',
                    'PBPX_', 'LSP_']

    def __init__(self, database, debug_mode: bool = False):
        self.debug_mode = debug_mode

        # Initialise the local classes
        self.db = database
        self.crc_verifier = CrcFileVerifier(debug_mode=self.debug_mode)
        self.bin_merger = BinMerger(debug_mode=self.debug_mode)
        self.ppf_patcher = PPFProcessor(debug_mode=self.debug_mode)


    # ************************************************************************************
    def _debug_print(self, message: str):
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(message)
    # ************************************************************************************


    # ************************************************************************************
    def _get_redump_tracks(self, game: Game) -> list:
        """Get the Redump track data from the local database"""

        # Get the Redump track info from the local database
        redump_tracks = self.db.get_track_info(game.get_id())
        tracks = []

        if not redump_tracks:
            return tracks

        # Convert to expected format
        for row in redump_tracks:
            try:
                track_number, pregap, sectors, size, crc = row

                # Validate and convert track_number, sectors, and size to integers
                try:
                    track_number = int(track_number)
                    sectors = int(sectors)
                    size = int(size)
                except ValueError as e:
                    print(f"Error converting track data {row}: {e}")
                    continue  # Skip this row if conversion fails

                # Convert pregap (MM:SS:FF) to sectors
                pregap_sectors = 0
                if pregap:
                    try:
                        parts = pregap.split(':')
                        if len(parts) != 3:
                            print(f"Warning: Invalid pregap format for track {track_number}: {pregap}. Expected MM:SS:FF.")
                            continue
                        minutes, seconds, frames = int(parts[0]), int(parts[1]), int(parts[2])
                        if not (0 <= seconds < 60 and 0 <= frames < 75):
                            print(f"Warning: Invalid pregap values for track {track_number}: {pregap}. Seconds must be < 60, frames < 75.")
                            continue
                        pregap_sectors = timecode_to_sectors(pregap)
                    except ValueError as e:
                        print(f"Error: Converting pregap '{pregap}' for track {track_number}: {e}")
                        continue

                # Handle crc safely
                crc_value = crc.lower() if crc and isinstance(crc, str) else ""

                tracks.append({
                    "track": track_number,
                    "pregap": pregap_sectors,
                    "sectors": sectors,
                    "size": size,
                    "crc32": crc_value
                })
            except Exception as e:
                print(f"Error processing track row {row}: {e}")
                continue

        return tracks
    # ************************************************************************************


    # ************************************************************************************
    def crc_check_bin(self, game: Game) -> bool:
        """Perform CRC-32 check on the BIN file/s and compare to the Redump data"""
        tracks_valid = False

        # Get the Redmup track info from the local database
        redump_tracks = self._get_redump_tracks(game)

        # Verify the tracks using the CUE file and Redump CRC-32 values
        if redump_tracks:
            tracks_valid = self.crc_verifier.verify_tracks(game.get_cue_sheet(), redump_tracks)

        return tracks_valid
    # ************************************************************************************


    # ************************************************************************************
    def find_cue_sheets(self, game_directory_path: str) -> list:
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
    def get_sub_folders(self, selected_path: str) -> list:
        """Get a list of sub-folders in the selected source directory"""

        if not selected_path or selected_path == "":
            return []

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
    def find_and_extract_game_archives(self, source_path: str, progress_callback=None) -> int:
        """Scan source_path for zip/7z/rar archives containing PS1 game files (bin+cue),
        extract any not yet extracted. Returns count of newly extracted archives."""
        supported = {'.zip'}
        if _PY7ZR_AVAILABLE:
            supported.add('.7z')
        if _RARFILE_AVAILABLE:
            supported.add('.rar')

        try:
            archive_entries = [
                e for e in scandir(source_path)
                if e.is_file() and not e.name.startswith('.')
                and splitext(e.name)[1].lower() in supported
            ]
        except OSError:
            return 0

        extracted_count = 0

        for entry in archive_entries:
            ext = splitext(entry.name)[1].lower()

            if progress_callback:
                progress_callback(f"Checking archive: {entry.name}")

            try:
                names = self._get_archive_names(entry.path, ext)
            except Exception as e:
                self._debug_print(f"Could not read archive '{entry.name}': {e}")
                continue

            if not names:
                continue

            lower_names = [n.lower() for n in names]
            if not (any(n.endswith('.bin') for n in lower_names) and
                    any(n.endswith('.cue') for n in lower_names)):
                continue

            root_dir = self._archive_single_root_dir(names)
            archive_stem = splitext(entry.name)[0]
            if root_dir:
                extract_to = source_path
                game_folder = join(source_path, root_dir)
            else:
                extract_to = join(source_path, archive_stem)
                game_folder = extract_to

            if exists(game_folder):
                has_cue = any(
                    f.lower().endswith('.cue')
                    for f in listdir(game_folder)
                    if isfile(join(game_folder, f))
                )
                if has_cue:
                    self._debug_print(f"Already extracted: {entry.name}")
                    continue
                # Folder exists but no .cue at root — incomplete or misplaced extraction
                self._debug_print(f"Removing bad extraction, retrying: {entry.name}")
                rmtree(game_folder, ignore_errors=True)

            if progress_callback:
                progress_callback(f"Extracting: {entry.name}")

            try:
                makedirs(extract_to, exist_ok=True)
                self._extract_archive(entry.path, ext, extract_to)
                extracted_count += 1
                self._debug_print(f"Extracted: {entry.name} -> {game_folder}")
            except Exception as e:
                self._debug_print(f"Error extracting '{entry.name}': {e}")
                if not root_dir and exists(game_folder) and not listdir(game_folder):
                    rmtree(game_folder, ignore_errors=True)

        return extracted_count
    # ************************************************************************************


    # ************************************************************************************
    def _get_archive_names(self, archive_path: str, ext: str) -> list:
        """Return list of entry names from an archive without extracting."""
        if ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as af:
                return af.namelist()
        elif ext == '.7z' and _PY7ZR_AVAILABLE:
            with py7zr.SevenZipFile(archive_path, 'r') as af:
                return af.getnames()
        elif ext == '.rar' and _RARFILE_AVAILABLE:
            with rarfile.RarFile(archive_path) as af:
                return af.namelist()
        return []
    # ************************************************************************************


    # ************************************************************************************
    def _extract_archive(self, archive_path: str, ext: str, extract_to: str):
        """Extract an archive to the given destination directory.
        For .7z files, prefers the native 7-Zip CLI (much faster than py7zr) and
        falls back to py7zr if 7-Zip is not installed."""
        if ext == '.7z':
            if _7ZIP_EXE and self._extract_with_7zip_cli(archive_path, extract_to):
                return
            if _PY7ZR_AVAILABLE:
                with py7zr.SevenZipFile(archive_path, 'r') as af:
                    af.extractall(extract_to)
        elif ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as af:
                af.extractall(extract_to)
        elif ext == '.rar' and _RARFILE_AVAILABLE:
            with rarfile.RarFile(archive_path) as af:
                af.extractall(extract_to)

    def _extract_with_7zip_cli(self, archive_path: str, extract_to: str) -> bool:
        """Extract using the system 7-Zip CLI. Returns True on success."""
        try:
            result = subprocess.run(
                [_7ZIP_EXE, 'x', archive_path, f'-o{extract_to}', '-y'],
                capture_output=True,
                timeout=600
            )
            return result.returncode == 0
        except Exception as e:
            self._debug_print(f"7-Zip CLI failed: {e}")
            return False
    # ************************************************************************************


    # ************************************************************************************
    def _archive_single_root_dir(self, names: list) -> Optional[str]:
        """If the game files (.bin/.cue) in the archive all share a single root directory,
        return that directory name. Returns None for flat archives (files at the root level).
        Only inspects .bin/.cue entries to avoid misidentifying 7z directory entries (which
        lack the trailing slash that ZIP uses) as flat files."""
        game_files = [
            n.replace('\\', '/') for n in names
            if n.lower().endswith('.bin') or n.lower().endswith('.cue')
        ]
        if not game_files:
            return None
        roots = set()
        for entry in game_files:
            parts = [p for p in entry.split('/') if p]
            if len(parts) == 1:
                return None  # game file is directly at the archive root — flat archive
            roots.add(parts[0])
        return next(iter(roots)) if len(roots) == 1 else None
    # ************************************************************************************


    # ************************************************************************************
    def libcrypt_already_applied(self, game: Game) -> bool:
        """Check if a LibCrypt patch has already been applied to the game"""

        # Return if the game does not require LibCrypt patching
        if not game.get_libcrypt_required():
            return False

        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        if self.db.copy_libcrypt_patch(game_full_path, game.get_id()):

            game_path = join(game.get_directory_path(), game.get_directory_name())
            bin_path = game.get_cue_sheet().get_bin_files()[0].get_file_path()
            ppf_path = f"{join(game_path, game.get_id())}.ppf"

            # If the PPF patch file has been copied, patch the BIN file
            if exists(ppf_path):
                # Open the BIN and PPF files
                bin_file, ppf_file = self.ppf_patcher.open_files(bin_path, ppf_path)
                if bin_file and ppf_file:
                    with bin_file, ppf_file:
                        is_applied = self.ppf_patcher.is_ppf_patch_applied(bin_file, ppf_file)
                        self._debug_print(f"LibCrypt Patch is {'already applied' if is_applied else 'not applied'}")

                        # Update the Game object to show that the LibCrypt checks have already been patched
                        if is_applied:
                            game.set_libcrypt_applied(True)

                    # Delete the extracted PPF file
                    remove(ppf_path)

        return game.get_libcrypt_applied()
    # ************************************************************************************


    # ************************************************************************************
    def is_multi_disc(self, game: Game) -> Optional[bool]:
        """Check if game is multi-disc"""
        return int(game.get_disc_number()) > 0 if game.get_disc_number() is not None else None
    # ************************************************************************************


    # ************************************************************************************
    def game_name_validator(self, game_name: str) -> str:
        """Validate game name length and characters"""

        # Handle empty or whitespace-only names
        game_name = game_name.strip()
        if not game_name:
            raise ValueError("Game name cannot be empty or whitespace-only")

        # Replace invalid characters in the game name
        sanitised_name = sub(self.INVALID_FILENAME_CHARS, '', game_name)

        # Truncate to maximum length
        sanitised_name = sanitised_name[:self.MAX_GAME_NAME_LENGTH]

        return sanitised_name
    # ************************************************************************************


    # ************************************************************************************
    def move_file(self, source_path: str, target_path: str):
        """Move a file from source to destination"""

        # Ensure that we only move files and not directories
        if not exists(source_path):
            print(f"(Error) Source file does not exist: {source_path}")
            return

        if isfile(source_path):
            try:
                move(source_path, target_path)
            except OSError as error:
                print(f"(Error) moving {source_path}: {error}")
    # ************************************************************************************


    # ************************************************************************************
    def rename_game(self, game: Game, new_game_name: str):
        """Rename game and associated files"""

        # Get the current game name from the CUE file
        cuesheet = game.get_cue_sheet()
        game_name = cuesheet.get_game_name()

        # If the game name and folder name are both already correct, nothing to do
        if game_name == new_game_name and game.get_directory_name() == new_game_name:
            return

        game_full_path = Path(game.get_directory_path()) / game.get_directory_name()
        new_game_dir = game_full_path.parent / new_game_name

        # If only the folder name is wrong (files are already correctly named), rename the folder in place
        if game_name == new_game_name:
            try:
                game_full_path.rename(new_game_dir)
                game.set_directory_name(new_game_name)
            except OSError as error:
                print(f"Error renaming folder '{game_full_path}': {error}")
            return

        # Get the BIN file (should be a single BIN file at this point)
        bin_file = cuesheet.get_bin_files()[0]

        # Get the original file paths
        original_cu2_path = game_full_path / f'{game_name}.cu2'
        original_bmp_path = game_full_path / f'{game_name}.bmp'

        # Create new directory for the game
        new_game_dir.mkdir(exist_ok=True)
        if not new_game_dir.exists():
            print(f"Error creating directory: {new_game_dir}")
            return

        # Move/rename the bin file
        if Path(bin_file.get_file_path()).exists():
            new_bin_path = new_game_dir / f'{new_game_name}.bin'
            self.move_file(bin_file.get_file_path(), new_bin_path)

            # Update the name and path of the Binfile object
            bin_file.set_file_name(f'{new_game_name}.bin')
            bin_file.set_file_path(new_bin_path)

        # Move/rename the cue file
        if Path(cuesheet.get_file_path()).exists():
            cue_path = Path(cuesheet.get_file_path())

            # Update the game name in the Cuesheet
            original_cue_text = cue_path.read_text()
            new_cue_text = original_cue_text.replace(game_name, new_game_name)
            cue_path.write_text(new_cue_text)
            new_cue_path = new_game_dir / f'{new_game_name}.cue'
            self.move_file(cuesheet.get_file_path(), new_cue_path)

            # Update the name and path of the Cuesheet object
            cuesheet.set_file_name(f'{new_game_name}.cue')
            cuesheet.set_file_path(new_cue_path)

        # Move/rename the cu2 file
        if original_cu2_path.exists():
            self.move_file(original_cu2_path, new_game_dir / f'{new_game_name}.cu2')

        # Move/rename the bmp file
        if original_bmp_path.exists():
            self.move_file(original_bmp_path, new_game_dir / f'{new_game_name}.bmp')

        # Update the Game objects paths
        game.set_directory_name(new_game_name)
        cuesheet.set_game_name(new_game_name)

        # Delete the original game directory if the game has moved to a new directory
        if game_full_path != new_game_dir:
            rmtree(game_full_path, ignore_errors=True)
    # ************************************************************************************


    # ************************************************************************************
    def _fix_cover_art(self, bmp_path: str) -> bool:
        """Ensure a BMP is 128x128 and 24-bit RGB. Resizes/converts in-place if needed.
        Returns True if the file was modified."""
        try:
            with Image.open(bmp_path) as img:
                if img.size == self.COVER_ART_SIZE and img.mode == 'RGB':
                    return False
                fixed = img.resize(self.COVER_ART_SIZE, Image.LANCZOS).convert('RGB')
            fixed.save(bmp_path, format='BMP')
            self._debug_print(f"Fixed cover art to 128x128 RGB: {bmp_path}")
            return True
        except Exception as e:
            self._debug_print(f"Error fixing cover art '{bmp_path}': {e}")
            return False
    # ************************************************************************************


    # ************************************************************************************
    def add_game_cover_art(self, game: Game):
        """Add the game cover art if missing; resize/convert to 128x128 24-bit BMP if wrong size"""
        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        game_name = game.get_cue_sheet().get_game_name()

        if game.get_cover_art_present():
            # Cover art exists — validate and fix dimensions/format if needed
            bmp_path = join(game_full_path, f'{game_name}.bmp')
            if not exists(bmp_path):
                bmp_path = join(game_full_path, f'{game_name}.BMP')
            if exists(bmp_path):
                self._fix_cover_art(bmp_path)
            return

        if self.db.copy_game_cover(game_full_path, game.get_id(), game_name):
            game.set_cover_art_present(True)
    # ************************************************************************************


    # ************************************************************************************
    def is_first_disc_without_multidisc(self, game: Game) -> bool:
        """Check if the game is the first disc without a multi-disc file."""
        return game.get_disc_number() == 1 and not game.get_multi_disc_file_present()
    # ************************************************************************************


    # ************************************************************************************
    def name_for_multidisc_folder(self, game_name: str) -> str:
        """Remove any text within parentheses (complete or incomplete), including the parentheses"""
        # First, remove complete parenthetical phrases
        cleaned = sub(r'\s*\([^)]*\)', '', game_name).strip()

        # Then, remove any trailing incomplete parentheses (open paren with no close at end)
        cleaned = sub(r'\s*\([^)]*$', '', cleaned).strip()

        return cleaned
    # ************************************************************************************


    # ************************************************************************************
    def detect_cdda(self, cue_file_path: str) -> bool:
        """Reads a CUE file and determines if it uses CDDA (CD Digital Audio) tracks"""
        try:
            with open(cue_file_path, 'r', encoding='utf-8', errors='replace') as file:
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
    def rename_game_using_redump(self, game: Game):
        """Rename the game using the game name from the Redump project"""

        game_id = game.get_id()
        redump_game_name = self.db.get_redump_name(game_id)

        if redump_game_name is not None and redump_game_name != "":
            # Validate the Redump game name
            redump_name = self.game_name_validator(redump_game_name)

            # Rename the game
            self.rename_game(game, redump_name)
    # ************************************************************************************


    # ************************************************************************************
    def is_name_valid(self, game_name: str) -> bool:
        """Return True if the game name is safe for PSIO (FAT32, no invalid chars, within length limit)"""
        return len(game_name) <= self.MAX_GAME_NAME_LENGTH and not search(self.INVALID_FILENAME_CHARS, game_name)
    # ************************************************************************************


    # ************************************************************************************
    def validate_game_name(self, game: Game):
        """Validate the game name"""
        game_name = game.get_cue_sheet().get_game_name()
        if not self.is_name_valid(game_name):
            new_game_name = self.game_name_validator(game_name).strip()

            if new_game_name != game_name:
                self.rename_game(game, new_game_name)
    # ************************************************************************************


    # ************************************************************************************
    def apply_libcrypt_patch(self, game: Game):
        """Apply LibCrypt PPF patch"""

        # Return if the game does not require LibCrypt patching or has already been patched
        if not game.get_libcrypt_required() or game.get_libcrypt_applied():
            return

        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        if self.db.copy_libcrypt_patch(game_full_path, game.get_id()):

            game_path = join(game.get_directory_path(), game.get_directory_name())
            bin_path = game.get_cue_sheet().get_bin_files()[0].get_file_path()
            ppf_path = f"{join(game_path, game.get_id())}.ppf"

            # If the PPF patch file has been copied, patch the BIN file
            if exists(ppf_path):
                bin_file, ppf_file = self.ppf_patcher.open_files(bin_path, ppf_path)

                if not bin_file or not ppf_file:
                    return

                with bin_file, ppf_file:
                    version = self.ppf_patcher.get_ppf_version(ppf_file)

                    if version == 1:
                        self.ppf_patcher.apply_ppf1_patch(ppf_file, bin_file)
                    elif version == 2:
                        self.ppf_patcher.apply_ppf2_patch(ppf_file, bin_file)
                    elif version == 3:
                        self.ppf_patcher.apply_ppf3_patch(ppf_file, bin_file)

                    # Update the Game object to show that the patch has been applied
                    game.set_libcrypt_applied(True)
                    game.set_crc_valid(False)

                # Delete the PPF patch file after it has been applied to the BIN file
                remove(ppf_path)
    # ************************************************************************************


    # ************************************************************************************
    def create_multi_disc_folder(self, multi_games: list[Game]):
        """Create a folder for the multi-disc game collection."""
        game_folder = self.name_for_multidisc_folder(multi_games[0].get_cue_sheet().get_game_name())
        new_game_path = join(multi_games[0].get_directory_path(), game_folder)
        makedirs(new_game_path, exist_ok=True)
        return new_game_path if exists(new_game_path) else None
    # ************************************************************************************


    # ************************************************************************************
    def update_game_paths(self, multi_disc: Game, game_path: str, game_folder: str, file_no_ext: str):
        """Update Game object paths"""
        multi_disc.set_directory_name(game_folder)

        bin_path = join(game_path, f"{file_no_ext}.bin")
        cue_path = join(game_path, f"{file_no_ext}.cue")

        multi_disc.get_cue_sheet().get_bin_files()[0].set_file_path(bin_path)
        multi_disc.get_cue_sheet().set_file_path(cue_path)
    # ************************************************************************************


    # ************************************************************************************
    def process_disc_files(self, multi_games: list[Game], new_game_path: str):
        """Move files for each disc and update game paths."""
        game_folder = self.name_for_multidisc_folder(multi_games[0].get_cue_sheet().get_game_name())

        for multi_disc in multi_games:
            if multi_disc:

                # Get the path for the disc
                disc_path = join(multi_disc.get_directory_path(), multi_disc.get_directory_name())

                if exists(disc_path):
                    for filename in listdir(disc_path):
                        source_path = join(disc_path, filename)
                        target_path = join(new_game_path, filename)
                        self.move_file(source_path, target_path)

                    # Update Game paths once per disc using the cue sheet name
                    file_no_ext = splitext(multi_disc.get_cue_sheet().get_file_name())[0]
                    self.update_game_paths(multi_disc, new_game_path, game_folder, file_no_ext)

                    rmtree(disc_path)
    # ************************************************************************************


    # ************************************************************************************
    def copy_multi_disc_cover_art(self, disc_1: Game, multi_games: list[Game]):
        """Duplicate the cover art from disc 1 for each of the multi-disc games, if missing"""

        if disc_1.get_cover_art_present():
            # Get the cover art for disc 1
            disc_1_path = join(disc_1.get_directory_path(), disc_1.get_directory_name())
            disc_1_bmp_path = join(disc_1_path, f"{disc_1.get_cue_sheet().get_game_name()}.bmp")

            if exists(disc_1_bmp_path):

                # Loop through the other discs in the collection and duplicate disc 1 cover art
                for multi_disc in multi_games:
                    if multi_disc:
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
    def generate_lst_file(self, multi_games: list[Game]):
        """Generate LST file"""
        game_path = join(multi_games[0].get_directory_path(), multi_games[0].get_directory_name())
        try:
            with open(join(game_path, "MULTIDISC.LST"), 'w', encoding="utf-8") as file:
                for multi_disc in multi_games:

                    if multi_disc:
                        file.write(f"{multi_disc.get_cue_sheet().get_game_name()}.bin" + '\n')

                        # Update the Game object to show that it now has an associated LST file
                        multi_disc.set_multi_disc_file_present(True)

        except OSError as error:
            print(f"Error creating multi-disc file: {error}")
    # ************************************************************************************


    # ************************************************************************************
    def generate_multidisc_files(self, game_list: list):
        """Generate MULTIDISC.LST file for all multi-disc games"""
        multi_disc_games = [game for game in game_list if game.get_disc_number() > 0]
        if not multi_disc_games:
            return

        # Build lookup once instead of rebuilding it for every disc in every collection
        game_lookup = {game.get_id(): game for game in game_list}

        for game in game_list:

            # Only process games that are disc 1 and LST file does not exist
            if not self.is_first_disc_without_multidisc(game):
                continue

            disc_collection = game.get_disc_collection()
            if not disc_collection:
                continue

            multi_games = [game_lookup.get(gid.replace('_', '-')) for gid in disc_collection]
            if any(g is None for g in multi_games):
                self._debug_print(f"Skipping multi-disc collection for '{game.get_id()}' — not all discs are present")
                continue
            if len(multi_games) <= 1:
                continue

            # Move the game files into a single directory and create the LST file
            new_game_path = self.create_multi_disc_folder(multi_games)
            self.process_disc_files(multi_games, new_game_path)
            self.generate_lst_file(multi_games)
            self.copy_multi_disc_cover_art(game, multi_games)
    # ************************************************************************************


    # ************************************************************************************
    def merge_bin_files(self, game: Game):
        """Merge multi-bin files"""

        # Get the game info
        cuesheet = game.get_cue_sheet()
        game_name = cuesheet.get_game_name()
        cue_file_name = cuesheet.get_file_name()
        game_full_path = join(game.get_directory_path(), game.get_directory_name())
        cue_full_path = join(game_full_path, cue_file_name)

        # Get the BIN files
        bin_files = cuesheet.get_bin_files()

        # Create a temporary directory to use whilst merging the bin files
        temp_game_dir = join(game_full_path, 'temp_dir')
        if not exists(temp_game_dir):
            try:
                makedirs(temp_game_dir, exist_ok=True)
            except OSError as error:
                print(f"ERROR: Creating temp game directory: {error}")
                return

        # Merge the BIN files
        bin_merged = self.bin_merger.merge(game_name, cue_file_name, bin_files, temp_game_dir)

        # Check if the single BIN and CUE files have been generated
        temp_bin_path = join(temp_game_dir, f'{game_name}.bin')
        temp_cue_path = join(temp_game_dir, cue_file_name)

        if bin_merged and exists(temp_bin_path) and exists(temp_cue_path):

            # Remove the original CUE file
            remove(cue_full_path)

            # Remove the original multi-bin files
            for original_bin_file in game.get_cue_sheet().get_bin_files():
                remove(original_bin_file.get_file_path())

            # Move the merged Bin file and the newly generated CUE file into the game directory
            self.move_file(temp_bin_path, join(game_full_path, f'{game_name}.bin'))
            self.move_file(temp_cue_path, join(game_full_path, cue_file_name))

            # Update the cuesheet object to have a single Binfile
            cuesheet.set_bin_files([bin_files[0]])

        # Remove the temporary directory
        rmtree(temp_game_dir)
    # ************************************************************************************


    # ************************************************************************************
    def parse_game_id(self, bin_file_path: str) -> Optional[str]:
        """Parse the unique game ID from BIN file"""
        if not exists(bin_file_path):
            return None

        with open(bin_file_path, 'rb') as bin_file:
            # PS1 SYSTEM.CNF is at LBA ~22; 50 sectors (117 KB) is more than enough
            data = bin_file.read(50 * 2352)

        # Decode as ASCII, dropping non-ASCII bytes, so region codes are searchable cleanly
        text = data.decode('ascii', errors='ignore')

        for region_code in self.REGION_CODES:
            if region_code in text:
                start = text.find(region_code)
                game_id = text[start:start + 11].replace('.', '').strip()
                return game_id.replace('_', '-').replace('.', '').strip()

        return None
    # ************************************************************************************


    # ************************************************************************************
    def parse_cue_file(self, cue_path: str) -> list[Binfile]:
        """Parse a CUE file to create Binfile objects with their Tracks and indexes"""
        bin_files = []
        current_file = None
        current_track = None
        bin_files_missing = False

        with open(cue_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()

                # Parse FILE line
                m = search(r'FILE\s+"(.+)"\s+BINARY', line)
                if m:
                    bin_file = m.group(1)
                    # Construct full path
                    file_path = join(dirname(cue_path), bin_file) if not isabs(bin_file) else bin_file
                    file_available = isfile(file_path) and access(file_path, R_OK)

                    # Try fallback names if file not found
                    if not file_available:
                        for replacement in [bin_file.replace(' (Track 01)', ''), bin_file.replace(' (Track 1)', '')]:
                            file_path = join(dirname(cue_path), replacement)
                            file_available = isfile(file_path) and access(file_path, R_OK)
                            if file_available:
                                break

                    if not file_available:
                        bin_files_missing = True
                        continue

                    current_file = Binfile(bin_file, file_path)
                    bin_files.append(current_file)
                    continue

                # Parse TRACK line
                m = search(r'TRACK\s+(\d+)\s+([^\s]+)', line)
                if m and current_file:
                    track_number = int(m.group(1))
                    track_type = m.group(2)
                    current_track = Track(track_number, track_type)
                    current_file.add_track(current_track)
                    continue

                # Parse INDEX line
                m = search(r'INDEX\s+(\d+)\s+(\d+:\d+:\d+)', line)
                if m and current_track:
                    index_id = int(m.group(1))
                    timestamp = m.group(2)
                    file_offset = timecode_to_sectors(timestamp)
                    current_track.add_index({'id': index_id, 'stamp': timestamp, 'file_offset': file_offset})
                    if index_id == 1:
                        current_track.set_file_offset(file_offset)
                    continue

                # Parse PREGAP (optional, for completeness)
                m = search(r'PREGAP\s+(\d+:\d+:\d+)', line)
                if m and current_track:
                    current_track.set_pregap(m.group(1))
                    continue

        if bin_files_missing:
            print(f'ERROR: Some binary files referenced in {cue_path} do not exist.')
            return []

        # Calculate sectors for tracks in single-file case
        if len(bin_files) == 1 and Track.globalBlocksize:
            next_item_offset = bin_files[0].get_size() // Track.globalBlocksize
            for track in reversed(bin_files[0].get_tracks()):
                if track.get_indexes() and track.get_indexes()[0]['id'] == 1:
                    track.set_sectors(next_item_offset - track.get_indexes()[0]['file_offset'])
                    next_item_offset = track.get_indexes()[0]['file_offset']

        return bin_files
    # ************************************************************************************
