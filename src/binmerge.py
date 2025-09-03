#!/usr/bin/env python3
#
#  binmerge
#
#  Takes a cue sheet with multiple binary track files and merges them together,
#  generating a corrected cue sheet in the process.
#
#  Copyright (C) 2020 Chris Putnam
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
#
#
#  This code has been modified by LoGi26 (2021) for use with the psio-assist script

from os import access, R_OK, name
from os.path import exists, join, dirname, isfile, getsize
from re import search, match
from typing import List, Union
from shutil import copyfileobj
import subprocess

# Global variables
ERROR_LOG_PATH = None


# ************************************************************************************
class Track:
    """A track within a binary file"""
    globalBlocksize = None

    def __init__(self, num, track_type):
        self.num = num
        self.indexes = []
        self.track_type = track_type
        self.sectors = None
        self.file_offset = None

        # All possible blocksize types. You cannot mix types on a disc, so we will use the first one we see and lock it in.
        if not Track.globalBlocksize:
            if track_type in ['AUDIO', 'MODE1/2352', 'MODE2/2352', 'CDI/2352']:
                Track.globalBlocksize = 2352
            elif track_type == 'CDG':
                Track.globalBlocksize = 2448
            elif track_type == 'MODE1/2048':
                Track.globalBlocksize = 2048
            elif track_type in ['MODE2/2336', 'CDI/2336']:
                Track.globalBlocksize = 2336
# ************************************************************************************


# ************************************************************************************
class File:
    """A binary file with its associated tracks and indexes"""
    def __init__(self, filename):
        self.filename = filename
        self.tracks = []
        self.size = getsize(filename)
# ************************************************************************************


# ************************************************************************************
class BinFilesMissingException(Exception):
    """Exception raised when one or more binary files referenced in the cue sheet are missing"""
    pass
# ************************************************************************************


# ************************************************************************************
def _sectors_to_cuestamp(sectors):
    """Convert sectors to a cue sheet timestamp (MM:SS:FF)"""
    minutes = sectors / 4500
    fields = sectors % 4500
    seconds = fields / 75
    fields = sectors % 75
    return '%02d:%02d:%02d' % (minutes, seconds, fields)
# ************************************************************************************


# ************************************************************************************
def _cuestamp_to_sectors(stamp):
    """Convert a cue sheet timestamp (MM:SS:FF) to sectors"""
    m = match('(\d+):(\d+):(\d+)', stamp)
    minutes = int(m.group(1))
    seconds = int(m.group(2))
    fields = int(m.group(3))
    return fields + (seconds * 75) + (minutes * 60 * 75)
# ************************************************************************************


# ************************************************************************************
def _gen_merged_cuesheet(basename, files):
    """generates a 'merged' cue sheet, that is, one bin file with tracks indexed within"""
    cue_sheet = f'FILE "{basename}.bin" BINARY\n'

    # One sector is (BLOCKSIZE) bytes
    sector_pos = 0
    for f in files:
        for t in f.tracks:
            cue_sheet += f'   TRACK {t.num} {t.track_type}\n'
            for i in t.indexes:
                cue_sheet += f'   INDEX {i["id"]} {_sectors_to_cuestamp(sector_pos + i["file_offset"])}\n'
            sector_pos += f.size / Track.globalBlocksize

    return cue_sheet
# ************************************************************************************


# ************************************************************************************
def _merge_files(merged_filename: str, files: List[Union[str, object]], use_native: bool = True, memory_merge: bool = False) -> bool:
    """Merge multiple binary files into a single output file"""

    # Validate target file
    if exists(merged_filename):
        print(f"Error: Target merged file already exists: {merged_filename}")
        raise FileExistsError(f"Target merged file already exists: {merged_filename}")

    # Validate and collect file paths
    file_paths = []
    for f in files:
        path = f.filename if hasattr(f, 'filename') else f
        if not isfile(path):
            print(f"Error: Input file does not exist or is not a file: {path}")
            raise FileNotFoundError(f"Input file does not exist or is not a file: {path}")
        file_paths.append(path)

    try:
        if use_native:
            # Use native OS commands for fastest merging
            if name == 'nt':  	# Windows
                cmd = 'copy /b ' + ' + '.join(f'"{path}"' for path in file_paths) + f' "{merged_filename}"'
                subprocess.run(cmd, shell=True, check=True)
            else:  				# Unix/Linux/macOS
                cmd = ['cat'] + file_paths + ['>', merged_filename]
                subprocess.run(' '.join(cmd), shell=True, check=True)
        else:
            # Fallback to memory-based or file-based merging
            if memory_merge:
                # Pre-read all files into memory (fast for small audio tracks)
                data = bytearray()
                for file_path in file_paths:
                    with open(file_path, 'rb') as in_file:
                        data.extend(in_file.read())
                with open(merged_filename, 'wb') as out_file:
                    out_file.write(data)
            else:
                # Sequential merging with shutil (faster than chunk-based)
                with open(merged_filename, 'wb') as out_file:
                    for file_path in file_paths:
                        with open(file_path, 'rb') as in_file:
                            copyfileobj(in_file, out_file)

        return True

    except (subprocess.CalledProcessError, IOError, OSError) as error:
        print(f"Error merging files: {error}")
        return False
# ************************************************************************************


# ************************************************************************************
def _log_error(error_type, error_message):
    """Log error messages to a file if the error log path is set"""
    if ERROR_LOG_PATH is not None:
        try:
            with open(ERROR_LOG_PATH, 'a+', encoding='utf-8') as error_log_file:
                error_log_file.write(f'[{error_type}]: {error_message}\n')
        except IOError:
            with open(ERROR_LOG_PATH, 'w', encoding='utf-8') as error_log_file:
                error_log_file.write(f'[{error_type}]: {error_message}\n')
# ************************************************************************************


# ************************************************************************************
def set_binmerge_error_log_path(log_path):
    """Set the path for the error log file"""
    global ERROR_LOG_PATH
    ERROR_LOG_PATH = log_path
# ************************************************************************************


# ************************************************************************************
def read_cue_file(cue_path):
    """Read and parse a cue file, returning a list of File objects with their tracks and indexes"""
    files = []
    this_track = None
    this_file = None
    bin_files_missing = False

    f = open(cue_path, 'r', encoding='utf-8')
    for line in f:
        m = search('FILE "?(.*?)"? BINARY', line)
        if m:
            this_path = join(dirname(cue_path), m.group(1))
            file_available = (isfile(this_path) or access(this_path, R_OK))

            if not file_available:
                this_path = join(dirname(cue_path), m.group(1).replace(' (Track 01)', ''))
                file_available = (isfile(this_path) or access(this_path, R_OK))
                if not file_available:
                    this_path = join(dirname(cue_path), m.group(1).replace(' (Track 1)', ''))
                    file_available = (isfile(this_path) or access(this_path, R_OK))

            if not file_available:
                bin_files_missing = True
            else:
                this_file = File(this_path)
                files.append(this_file)

            continue

        m = search('TRACK (\d+) ([^\s]*)', line)
        if m and this_file:
            this_track = Track(int(m.group(1)), m.group(2))
            this_file.tracks.append(this_track)
            continue

        m = search('INDEX (\d+) (\d+:\d+:\d+)', line)
        if m and this_track:
            this_track.indexes.append({'id': int(m.group(1)), 'stamp': m.group(2), 'file_offset':_cuestamp_to_sectors(m.group(2))})
            continue

    if bin_files_missing:
        _log_error('ERROR', f'file does not exist: {line}')
        return []

    if len(files) == 1:
        # only 1 file, assume splitting, calc sectors of each
        next_item_offset = files[0].size // Track.globalBlocksize
        for t in reversed(files[0].tracks):
            t.sectors = next_item_offset - t.indexes[0]["file_offset"]
            next_item_offset = t.indexes[0]["file_offset"]

    return files
# ************************************************************************************


# ************************************************************************************
def start_bin_merge(cue_file, game_name, out_dir):
    """Main function to start the bin merging process"""
    cue_map = read_cue_file(cue_file)
    cue_sheet = _gen_merged_cuesheet(game_name, cue_map)

    if not exists(out_dir):
        _log_error('ERROR', 'Output dir does not exist')
        return False

    new_cue_fn = join(out_dir, game_name + '.cue')
    if exists(new_cue_fn):
        _log_error('ERROR', f'Output cue file already exists. Quitting. Path: {new_cue_fn}')
        return False

    if not _merge_files(join(out_dir, game_name + '.bin'), cue_map):
        return False

    with open(new_cue_fn, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(cue_sheet)

    return True
# ************************************************************************************
