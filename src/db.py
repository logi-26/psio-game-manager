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
	except sqlite3.Error as error:
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
	if exists(join(DATABASE_PATH, 'fs_manifest.csv')):
		remove(join(DATABASE_PATH, 'fs_manifest.csv'))
# *****************************************************************************************************************


# *****************************************************************************************************************
# Function that merges the split database files
def _merge_database():
	fs = Filesplit()
	fs.merge(input_dir=DATABASE_PATH)
	_delete_database_splits()
# *****************************************************************************************************************
