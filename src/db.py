'''
Sqlite3 database functions
The application uses a local Sqlite3 database to store game names and game cover art

The local database file has been split into 4 separate files in the repo
This is due to the 100MB file size limit in GitHub
The application will merge the split database files into a single file when it is launched
'''

from sys import exit
from os import remove, makedirs
from os.path import exists, join, getsize
from sqlite3 import connect, Error
from pathlib2 import Path

DATABASE_PATH = None
DATABASE_FILE = None
DATABASE_FULL_PATH = None


# ************************************************************************************
def _split_database():
    """Splits the database file into 4 equal parts"""
    # Create output directory if it doesn't exist
    if not exists(DATABASE_PATH):
        makedirs(DATABASE_PATH)

    # Get file size
    file_size = getsize(DATABASE_FULL_PATH)
    chunk_size = file_size // 4

    # Read input file in binary mode
    with open(DATABASE_FULL_PATH, 'rb') as f:
        for i in range(4):
            # Calculate size for this chunk (last chunk might be slightly larger)
            if i == 3:
                chunk_size = file_size - (chunk_size * 3)

            # Read chunk data
            chunk_data = f.read(chunk_size)

            # Write chunk to new file
            output_path = join(DATABASE_PATH, f'psio_assist_db_part_{i+1}')
            with open(output_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)
# ************************************************************************************


# ************************************************************************************
def _merge_database():
    """Merges the 4 split database files back into a single file"""
    # Open output file in binary write mode
    with open(DATABASE_FULL_PATH, 'wb') as outfile:
        # Merge files in order (part_1 to part_4)
        for i in range(1, 5):
            part_path = join(DATABASE_PATH, f'psio_assist_db_part_{i}')
            if not exists(part_path):
                raise FileNotFoundError(f"Part file {part_path} not found")

            # Read and write each part
            with open(part_path, 'rb') as infile:
                outfile.write(infile.read())

    # Delete the split files after merging
    _delete_database_splits()
# ************************************************************************************


# ************************************************************************************
def _database_splits_exist():
    """Checks if each of the database split-files exist"""
    for i in range(1,5):
        if not exists(join(DATABASE_PATH, f'psio_assist_db_part_{i}')):
            return False
    return True
# ************************************************************************************


# ************************************************************************************
def _delete_database_splits():
    """Delete the database split-files"""
    for i in range(1,5):
        if exists(join(DATABASE_PATH, f'psio_assist_db_part_{i}')):
            remove(join(DATABASE_PATH, f'psio_assist_db_part_{i}'))
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
def set_database_path(database_path: str, database_name: str):
    """Set the database path based on whether the application is running as a script or an exe"""
    global DATABASE_PATH, DATABASE_FILE, DATABASE_FULL_PATH
    DATABASE_PATH = database_path
    DATABASE_FILE = database_name
    DATABASE_FULL_PATH = join(DATABASE_PATH, DATABASE_FILE)
# ************************************************************************************


# ************************************************************************************
def ensure_database_exists():
    """Ensures that the database file exists and has been merged into a single file"""
    if not exists(DATABASE_FULL_PATH):
        if _database_splits_exist():
            _merge_database()
            if not exists(DATABASE_FULL_PATH):
                print('\n******************************')
                print('Unable to merge database file!')
                print('******************************\n')
                exit()
        else:
            print('\n******************************')
            print('Database split-files not found!')
            print('******************************\n')
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
    """Get the game name using names from Redump/PSX Data-Centre stored in a local database"""

    formatted_game_id = game_id.replace('-','_')
    query = f'SELECT name FROM games WHERE game_id = "{formatted_game_id}"'
    response = select(f'''{query};''')

    if response is not None and response != []:
        game_name = response[0][0]
        return game_name

    return ''
# ************************************************************************************


# ************************************************************************************
def get_disc_number(game_id: str):
    """Get the disc number from the local database"""

    formatted_game_id = game_id.replace('-','_')
    query = f'SELECT disc_number FROM games WHERE game_id = "{formatted_game_id}"'
    response = select(f'''{query};''')

    return response[0][0] if response and response != [] else 0
# ************************************************************************************


# ************************************************************************************
def get_libcrypt_status(game_id: str):
    """Get the libcrypt status from local database"""

    formatted_game_id = game_id.replace('-','_')
    query = f'SELECT libcrypt FROM games WHERE game_id = "{formatted_game_id}"'
    response = select(f'''{query};''')

    return response[0][0] if response and response != [] else 0
# ************************************************************************************


# ************************************************************************************
def libcrypt_patch_available(game_id: str) -> bool:
    """Check if there is a LibCrypt PPF patch available in the local database"""

    formatted_game_id = game_id.replace('-','_')
    query = f'SELECT id FROM libcrypt_patches WHERE game_id = "{formatted_game_id}"'
    response = select(f'''{query};''')

    return response and response != []
# ************************************************************************************


# ************************************************************************************
def copy_game_cover(output_path: str, game_id: str, game_name: str):
    """Copy the game front cover art if it is available in the local database"""

    formatted_game_id = game_id.replace('-','_')
    query = f'SELECT id FROM covers WHERE game_id = "{formatted_game_id}"'
    response = select(f'''{query};''')

    if response and response != []:
        row_id = response[0][0]

        image_out_path = join(output_path, f'{game_name}.bmp')
        _extract_game_cover_blob(row_id, image_out_path)
# ************************************************************************************


# ************************************************************************************
def copy_libcrypt_patch(output_path: str, game_id: str):
    """Copy the LibCrypt PPF patch file if it is available in the local database"""

    formatted_game_id = game_id.replace('-','_')
    query = f'SELECT id FROM libcrypt_patches WHERE game_id = "{formatted_game_id}"'
    response = select(f'''{query};''')

    if response and response != []:
        row_id = response[0][0]
        ppf_out_path = join(output_path, f'{game_id}.ppf')
        _extract_game_libcrypt_patch_blob(row_id, ppf_out_path)
# ************************************************************************************
