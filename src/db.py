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
def _extract_game_cover_blob(row_id, image_out_path: str):
    """Extract the game cover art data from the local database"""
    try:
        conn = _create_connection(DATABASE_FULL_PATH)
        cursor = conn.cursor()

        with open(image_out_path, 'wb') as output_file:
            cursor.execute(f'SELECT psio FROM covers WHERE id = {row_id};')
            image_blob = cursor.fetchone()
            output_file.write(image_blob[0])

        cursor.close()
    except Error:
        pass
    finally:
        if conn:
            conn.close()
# ************************************************************************************


# ************************************************************************************
def _extract_game_libcrypt_patch_blob(row_id, ppf_out_path: str):
    """Extract the game LibCrypt PPF patch data from the local database"""
    try:
        conn = _create_connection(DATABASE_FULL_PATH)
        cursor = conn.cursor()

        with open(ppf_out_path, 'wb') as output_file:
            cursor.execute(f'SELECT psio FROM libcrypt_patches WHERE id = {row_id};')
            patch_blob = cursor.fetchone()
            output_file.write(patch_blob[0])

        cursor.close()
    except Error:
        pass
    finally:
        if conn:
            conn.close()
# ************************************************************************************


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
def select(select_query: str):
    """Select data from the local database"""
    rows = []
    try:
        conn = _create_connection(DATABASE_FULL_PATH)
        cursor = conn.cursor()
        cursor.execute(select_query)
        rows = cursor.fetchall()
        cursor.close()
    except Error:
        pass
    finally:
        if conn:
            conn.close()

    return rows
# ************************************************************************************


# ************************************************************************************
def get_redump_name(game_id: str):
    """Get the game name using names from Redump and the PSX Data-Centre stored in a local database file"""
    response = select(f'''SELECT name FROM games WHERE game_id = "{game_id.replace('-','_')}";''')
    if response is not None and response != []:
        game_name = response[0][0]
        return game_name

    return ''
# ************************************************************************************


# ************************************************************************************
def get_disc_number(game_id: str):
    """Get the disc number from the local database"""
    response = select(f'''SELECT disc_number FROM games WHERE game_id = "{game_id.replace('-','_')}";''')
    return response[0][0] if response and response != [] else 0
# ************************************************************************************


# ************************************************************************************
def get_libcrypt_status(game_id: str):
    """Get the libcrypt status from local database"""
    response = select(f'''SELECT libcrypt FROM games WHERE game_id = "{game_id.replace('-','_')}";''')
    return response[0][0] if response and response != [] else 0
# ************************************************************************************


# ************************************************************************************
def libcrypt_patch_available(game_id: str) -> bool:
    """Check if there is a LibCrypt PPF patch available in the local database"""
    response = select(f'''SELECT id FROM libcrypt_patches WHERE game_id = "{game_id.replace('-','_')}";''')
    return True if response and response != [] else False
# ************************************************************************************


# ************************************************************************************
def copy_game_cover(output_path: str, game_id: str, game_name: str):
    """Copy the game front cover art if it is available in the local database"""
    response = select(f'''SELECT id FROM covers WHERE game_id = "{game_id.replace('-','_')}";''')
    if response and response != []:
        row_id = response[0][0]

        image_out_path = join(output_path, f'{game_name}.bmp')

        print(f"\nimage_out_path: {image_out_path}\n")

        _extract_game_cover_blob(row_id, image_out_path)
# ************************************************************************************


# ************************************************************************************
def copy_libcrypt_patch(output_path: str, game_id: str):
    """Copy the LibCrypt PPF patch file if it is available in the local database"""
    response = select(f'''SELECT id FROM libcrypt_patches WHERE game_id = "{game_id.replace('-','_')}";''')
    if response and response != []:
        row_id = response[0][0]
        ppf_out_path = join(output_path, f'{game_id}.ppf')
        _extract_game_libcrypt_patch_blob(row_id, ppf_out_path)
# ************************************************************************************
