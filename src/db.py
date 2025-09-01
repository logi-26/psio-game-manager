'''
Sqlite3 database functions
The application uses a local Sqlite3 database to store game names and game cover art

The local database file has been split into 4 separate files in the repo
This is due to the 100MB file size limit in GitHub
The application will merge the split database files into a single file when it is launched
'''

from sys import argv
from os import remove
from os.path import exists, join, abspath, dirname
from sqlite3 import connect, Error
from filesplit.merge import Merge
from pathlib2 import Path

DATABASE_PATH = join(Path(abspath(dirname(argv[0]))), 'data')
DATABASE_FILE = 'psio_assist.db'
DATABASE_MANIFEST_FILE = 'fs_manifest.csv'
DATABASE_FULL_PATH = join(DATABASE_PATH, DATABASE_FILE)


# ************************************************************************************
def ensure_database_exists():
    """Ensures that the database file exists and has been merged into a single file"""
    if not exists(DATABASE_FULL_PATH):
        if _database_splits_exist():
            _merge_database()
            if not exists(DATABASE_FULL_PATH):
                print('Unable to merge database file!')
                exit()
        else:
            print('Database split-files not found!')
            exit()
# ************************************************************************************


# ************************************************************************************
def _database_splits_exist():
    """Checks if each of the database split-files exist"""
    for i in range(1,5):
        if not exists(join(DATABASE_PATH, f'psio_assist_{i}.db')):
            return False
    if not exists(join(DATABASE_PATH, 'fs_manifest.csv')):
        return False
    return True
# ************************************************************************************


# ************************************************************************************
def _merge_database():
    """Merge the split database files into a single file"""
    #fs = Filesplit()
    #fs.merge(input_dir=DATABASE_PATH)
    Merge(DATABASE_PATH, DATABASE_PATH, DATABASE_FILE)
    
    _delete_database_splits()
# ************************************************************************************


# ************************************************************************************
def _delete_database_splits():
    """Delete the database split-files"""
    for i in range(1,5):
        if exists(join(DATABASE_PATH, f'psio_assist_{i}.db')):
            remove(join(DATABASE_PATH, f'psio_assist_{i}.db'))
    if exists(join(DATABASE_PATH, DATABASE_MANIFEST_FILE)):
        remove(join(DATABASE_PATH, DATABASE_MANIFEST_FILE))
# ************************************************************************************


# ************************************************************************************
def _create_connection(db_file):
    """Establish a connection with the local Sqlite3 database"""
    conn = None
    try:
        conn = connect(db_file)
        return conn
    except Error as error:
        print(error)

    return conn
# ************************************************************************************


# ************************************************************************************
def select(select_query):
    """Select data from the local database"""
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
# ************************************************************************************


# ************************************************************************************
def extract_game_cover_blob(row_id, image_out_path):
    """Extract the game cover art data from the local database"""
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
# ************************************************************************************


# ************************************************************************************
def extract_game_libcrypt_patch_blob(row_id, ppf_out_path):
    """Extract the game LibCrypt PPF patch data from the local database"""
    try:
        conn = _create_connection(DATABASE_FULL_PATH)
        cursor = conn.cursor()

        with open(ppf_out_path, 'wb') as output_file:
            cursor.execute(f'SELECT psio FROM libcrypt_patches WHERE id = {row_id};')
            ablob = cursor.fetchone()
            output_file.write(ablob[0])

        cursor.close()
    except Error as error:
        print(error)
        pass
    finally:
        if conn:
            conn.close()
# ************************************************************************************
