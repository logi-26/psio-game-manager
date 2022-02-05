'''
Sqlite3 database functions
'''

# System imports
from sys import argv, exit
from os import remove
from os.path import exists, join, abspath, dirname
from pathlib2 import Path
from sqlite3 import connect, Error
from fsplit.filesplit import Filesplit

DATABASE_PATH = join(Path(abspath(dirname(argv[0]))), 'data')
DATABASE_FILE = 'psio_assist.db'
DATABASE_MANIFEST_FILE = 'fs_manifest.csv'
DATABASE_FULL_PATH = join(DATABASE_PATH, DATABASE_FILE)


# *****************************************************************************************************************
# Function that ensures the database file exists and has been merged
def ensure_database_exists():
	if not exists(DATABASE_FULL_PATH):
		if _database_splits_exist():
			_merge_database()
			if not exists(DATABASE_FULL_PATH):
				print('Unable to merge database file!')
				exit()
		else:
			print('Database split-files not found!')
			exit()
# *****************************************************************************************************************


# *****************************************************************************************************************
def select(select_query):
	rows = []
	try:
		conn = _create_connection(DATABASE_FULL_PATH)
		cursor = conn.cursor()
		cursor.execute(select_query)
		rows = cursor.fetchall()
		cursor.close()
	except Error as error:
		pass
	finally:
		if conn:
			conn.close()

	return rows
# *****************************************************************************************************************


# *****************************************************************************************************************
def _create_connection(db_file):
	conn = None
	try:
		conn = connect(db_file)
		return conn
	except Error as error:
		print(error)

	return conn
# *****************************************************************************************************************






# **********************************************************************************************************************
def extract_game_cover_blob(row_id, image_out_path):
	try:
		conn = _create_connection(DATABASE_FULL_PATH)
		cursor = conn.cursor()

		with open(image_out_path, 'wb') as output_file:
		    cursor.execute(f'SELECT psio FROM covers WHERE id = {row_id};')
		    ablob = cursor.fetchone()
		    output_file.write(ablob[0])

		cursor.close()
	except Error as error:
		print(error)
		pass
	finally:
		if conn:
			conn.close()
 # **********************************************************************************************************************










# *****************************************************************************************************************
# Function that checks if each of the database split-files exist
def _database_splits_exist():
	for i in range(1,5):
		if not exists(join(DATABASE_PATH, f'psio_assist_{i}.db')):
			return False
	if not exists(join(DATABASE_PATH, 'fs_manifest.csv')):
		return False
	return True
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that deletes the database split-files
def _delete_database_splits():
	for i in range(1,5):
		if exists(join(DATABASE_PATH, f'psio_assist_{i}.db')):
			remove(join(DATABASE_PATH, f'psio_assist_{i}.db'))
	if exists(join(DATABASE_PATH, DATABASE_MANIFEST_FILE)):
		remove(join(DATABASE_PATH, DATABASE_MANIFEST_FILE))
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that merges the split database files
def _merge_database():
	fs = Filesplit()
	fs.merge(input_dir=DATABASE_PATH)
	_delete_database_splits()
# *****************************************************************************************************************
