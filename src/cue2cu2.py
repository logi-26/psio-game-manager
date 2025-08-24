#!/usr/bin/env python3
# cue2cu2 - converts a cue sheet to CU2 format.
# Originally written by NRGDEAD in 2019. Use at your own risk.
# This program was written based on my web research and my reverse engineering of the CU2 format.
# Sorry, this is my first Python thingie. I have no idea what I'm doing. Thanks.
# WWW: https://github.com/NRGDEAD/Cue2cu2

# Copyright 2019-2020 NRGDEAD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#  This code has been modified by LoGi26 (2021) for use with the psio-assist script


from os import remove
from os.path import exists, join, getsize
from pathlib import Path
from re import compile

# Global variables
error_log_path = None


# **********************************************************************************************************
# Function to convert timecode/index position to sector count
def _convert_timecode_to_sectors(timecode):
	minutes = int(timecode[0:2])
	seconds = int(timecode[3:5])
	sectors = int(timecode[6:8])
	minutes_sectors = int(minutes*60*75)
	seconds_sectors = int(seconds*75)
	total_sectors = int(minutes_sectors + seconds_sectors + sectors)
	return total_sectors
# **********************************************************************************************************


# **********************************************************************************************************
# Function to convert sectors to timcode
def _convert_sectors_to_timecode(sectors):
	total_seconds = int(int(sectors)/75)
	modulo_sectors = int(int(sectors)%75)
	total_minutes = int(total_seconds/60)
	modulo_seconds = int(total_seconds%60)
	timecode = f'{str(total_minutes).zfill(2)}:{str(modulo_seconds).zfill(2)}:{str(modulo_sectors).zfill(2)}'
	return timecode
# **********************************************************************************************************


# **********************************************************************************************************
# Function to convert sectors to timcode - but use MM:SS-1:75 instead of MM:SS:00. Thanks for finding that oddity, bikerspade!
def _convert_sectors_to_timecode_with_alternative_notation(sectors):
	total_seconds = int(int(sectors)/75)
	modulo_sectors = int(int(sectors)%75)
	total_minutes = int(total_seconds/60)
	modulo_seconds = int(total_seconds%60)
	if modulo_sectors == 0:
		modulo_sectors = int(75)
		if modulo_seconds != 0:
			modulo_seconds = modulo_seconds - 1
		else:
			modulo_seconds = 59
			total_minutes = total_minutes - 1
	timecode = f'{str(total_minutes).zfill(2)}:{str(modulo_seconds).zfill(2)}:{str(modulo_sectors).zfill(2)}'
	return timecode
# **********************************************************************************************************


# **********************************************************************************************************
# Function to get the total runtime timecode for a given filesize
def _convert_bytes_to_sectors(filesize):
	if filesize % 2352 == 0:
		return int(int(filesize)/2352)
# **********************************************************************************************************


# **********************************************************************************************************
# Function to get the total runtime timecode for a given file
def _convert_filesize_to_sectors(binaryfile):
	if exists(binaryfile):
		return _convert_bytes_to_sectors(getsize(binaryfile))
# **********************************************************************************************************


# **********************************************************************************************************
# Function to add two timecodes together
def _timecode_addition(timecode, offset):
	result = _convert_timecode_to_sectors(timecode) + _convert_timecode_to_sectors(offset)
	if result > int('449999'):
		result = int('449999')
	return _convert_sectors_to_timecode(result)
# **********************************************************************************************************


# **********************************************************************************************************
# Function to log basic error messages to a file
def _log_error(error_type, error_message):
	if error_log_path is not None:
		try:
			with open(error_log_path, 'a+') as error_log_file:
				error_log_file.write(f'[{error_type}]: {error_message}\n')
		except IOError:
			with open(error_log_path, 'w') as error_log_file:
				error_log_file.write(f'[{error_type}]: {error_message}\n')
# **********************************************************************************************************


# **********************************************************************************************************
# Function to set the error log path
def set_cu2_error_log_path(log_path):
	global error_log_path
	error_log_path = log_path
# **********************************************************************************************************


# **********************************************************************************************************
# SCRIPT START
# **********************************************************************************************************
def start_cue2cu2(cuesheet, binaryfile_name):
	# Hardcoded for CU2 revision 2
	format_revision = int(2)

	# Copy the cue sheet into an array so we don't have to re-read it from disk again and can navigate it easily
	try:
		with open(cuesheet,'r') as cuesheet_file:
			cuesheet_content = cuesheet_file.read().splitlines()
			cuesheet_file.close
	except:
		_log_error('ERROR', f'Could not open {str(cuesheet)}')
		return False

	# Check the cue sheet if the image is supposed to be in Mode 2 with 2352 bytes per sector
	for line in cuesheet_content:
		cuesheet_mode_valid = bool(False)
		if compile('.*[Mm][Oo][Dd][Ee]2/2352.*').match(line):
			cuesheet_mode_valid = bool(True)
			break
	if cuesheet_mode_valid == False: # If it's not, we can't continue
		_log_error('ERROR', f'Cue sheet {str(cuesheet)} indicates this image is not in MODE2/2352')
		return False

	bin_path = str(Path(cuesheet).parent)
	binaryfile = join(bin_path, binaryfile_name)
	output = str()

	# Get number of tracks from cue sheet
	ntracks = 0
	for line in cuesheet_content:
		if compile('[ \t]*[Tt][Rr][Aa][Cc][Kk].*').match(line) and not compile('[ \t]*[Ff][Ii][Ll][Ee].*[Tt][Rr][Aa][Cc][Kk].*').match(line):
			ntracks += 1
	output = f'{output}ntracks {str(ntracks)}\r\n'

	sectors = _convert_filesize_to_sectors(binaryfile)

	if sectors is None:
		return False

	# Get the total runtime/size
	size = _convert_sectors_to_timecode(sectors)
	output = f'{output}size	   {size}\r\n'

	# Get data1 - well, this is always the same for our kind of disc images, so...
	# At some point I should do this the proper way and grab it from Track 1.
	data1 = _timecode_addition('00:00:00','00:02:00')
	output = f'{output}data1	   {data1}\r\n'

	# Get the track and pregap lengths
	pregap_command_used_before = bool(False)
	for track in range(2, ntracks+1):
		# Find current track number in cuesheet_content
		current_track_in_cuesheet = -1;
		for line in cuesheet_content:
			current_track_in_cuesheet += 1
			if compile(f'.*[Tt][Rr][Aa][Cc][Kk] 0?{str(track)}.*').match(line):
				break

		# See if the next line is index 00, and if so, get and output the pregap if the CU2 format requires it
		if compile('.*[Ii][Nn][Dd][Ee][Xx] 0?0.*').match(cuesheet_content[current_track_in_cuesheet+1]) and format_revision == int(2):
			pregap_position = cuesheet_content[current_track_in_cuesheet+1][::-1][:8][::-1][:9]

			# Add the famous two second offset for PSIO and convert to alternative notation used by Systems Console for tracks
			pregap_position = _convert_sectors_to_timecode_with_alternative_notation(_convert_timecode_to_sectors(_timecode_addition(pregap_position,"00:02:00")))
			output = f'{output}pregap{str(track).zfill(2)}	{pregap_position}\r\n'

		# Check if this cue sheet uses the PREGAP command, which is bad. We can continue, but...
		elif compile('.*[Pp][Rr][Ee][Gg][Aa][Pp].*').match(cuesheet_content[current_track_in_cuesheet+1]) and format_revision == int(2):
			if pregap_command_used_before == False:
				_log_error('WARNING', f'The PREGAP command is used for track {str(track)}, which requires the software to insert data into the image or disc. This is not supported by Cue2cu2. The pregap will be ignored and a zero length pregap will be noted in the CU2 sheet in order to continue, but the resulting bin/CU2 set might not work as expected or not at all. If possible, please try a Redump compatible version of this image')
				pregap_command_used_before = bool(True)
			elif pregap_command_used_before == True:
				_log_error('WARNING', f'The PREGAP command is also used for track {str(track)}.')
			if compile('.*[Ii][Nn][Dd][Ee][Xx] 0?1.*').match(cuesheet_content[current_track_in_cuesheet+2]):
				pregap_position = cuesheet_content[current_track_in_cuesheet+2][::-1][:8][::-1][:9]

				# Add the famous two second offset for PSIO and convert to alternative notation used by Systems Console for tracks
				pregap_position = _convert_sectors_to_timecode_with_alternative_notation(_convert_timecode_to_sectors(_timecode_addition(pregap_position,"00:02:00")))
				output = f'{output}pregap{str(track).zfill(2)}	{pregap_position}\r\n'

		elif format_revision == int(2):
			_log_error('ERROR', f'Could not find pregap position (index 00) for track {str(track)} in cue sheet: {str(cuesheet)}')
			return False

		# Else-If is it index 01? If so, output track start, or get it from the following line
		if compile('.*[Ii][Nn][Dd][Ee][Xx] 0?1.*').match(cuesheet_content[current_track_in_cuesheet+1]):
			track_position = cuesheet_content[current_track_in_cuesheet+1][::-1][:8][::-1][:9] # I have no idea what I'm doing
		elif compile('.*[Ii][Nn][Dd][Ee][Xx] 0?1.*').match(cuesheet_content[current_track_in_cuesheet+2]):
			track_position = cuesheet_content[current_track_in_cuesheet+2][::-1][:8][::-1][:9]
		else:
			_log_error('ERROR', f'Could not find starting position (index 01) for track {str(track)} in cue sheet: {str(cuesheet)}')
			return False

		# Add the famous two second offset for PSIO and convert to alternative notation used by Systems Console for tracks
		track_position = _convert_sectors_to_timecode_with_alternative_notation(_convert_timecode_to_sectors(_timecode_addition(track_position,"00:02:00")))
		output = f'{output}track{str(track).zfill(2)}	{track_position}\r\n'

	# Add the end for the last track
	track_end = _convert_sectors_to_timecode_with_alternative_notation(_convert_timecode_to_sectors(_timecode_addition(size,'00:02:00')))
	output = f'{output}\r\ntrk end	 {track_end}'

	# *********************************************
	# We are now ready to output our CU2 sheet
	# *********************************************

	# Derive the file name from the binary file's filename
	cu2sheet = binaryfile[::-1][4:][::-1]+'.cu2'
	try:
		cu2file = open(cu2sheet,'wb')
		cu2file.write(output.encode())
		cu2file.close
	except:
		_log_error('ERROR', f'Could not write to: {str(cu2sheet)}')
		return False

	return True
# **********************************************************************************************************
