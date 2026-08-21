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
from threading import Lock


class GameDatabase:
    """Manages SQLite3 database operations for game data and assets"""
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self._database_path = None
        self._database_file = None
        self._database_full_path = None
        self._conn = None
        self._lock = Lock()


    # ************************************************************************************
    def _debug_print(self, message: str):
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(message)
    # ************************************************************************************


    # ************************************************************************************
    def _split_database(self):
        """Splits the database file into 4 equal parts"""
        if not exists(self._database_path):
            makedirs(self._database_path)

        file_size = getsize(self._database_full_path)
        chunk_size = file_size // 4

        with open(self._database_full_path, 'rb') as f:
            for i in range(4):
                if i == 3:
                    chunk_size = file_size - (chunk_size * 3)

                chunk_data = f.read(chunk_size)
                output_path = join(self._database_path, f'psio_assist_db_part_{i+1}')
                with open(output_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
    # ************************************************************************************


    # ************************************************************************************
    def _merge_database(self):
        """Merges the 4 split database files back into a single file"""
        with open(self._database_full_path, 'wb') as outfile:
            for i in range(1, 5):
                part_path = join(self._database_path, f'psio_assist_db_part_{i}')
                if not exists(part_path):
                    raise FileNotFoundError(f"Part file {part_path} not found")

                with open(part_path, 'rb') as infile:
                    outfile.write(infile.read())

        self._delete_database_splits()
    # ************************************************************************************


    # ************************************************************************************
    def _database_splits_exist(self):
        """Checks if each of the database split-files exist"""
        for i in range(1, 5):
            if not exists(join(self._database_path, f'psio_assist_db_part_{i}')):
                return False
        return True
    # ************************************************************************************


    # ************************************************************************************
    def _delete_database_splits(self):
        """Delete the database split-files"""
        for i in range(1, 5):
            part_path = join(self._database_path, f'psio_assist_db_part_{i}')
            if exists(part_path):
                remove(part_path)
    # ************************************************************************************


    # ************************************************************************************
    def _open_connection(self):
        """Open the persistent database connection"""
        try:
            # check_same_thread=False allows background threads to share the connection;
            # the Lock serialises access so concurrent queries don't race.
            self._conn = connect(self._database_full_path, check_same_thread=False)
        except Error as error:
            print(error)
            self._conn = None
    # ************************************************************************************


    # ************************************************************************************
    def close(self):
        """Close the persistent database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None
    # ************************************************************************************


    # ************************************************************************************
    def set_database_path(self, database_path: str, database_name: str):
        """Set the database path based on whether running as script or executable"""
        self._database_path = database_path
        self._database_file = database_name
        self._database_full_path = join(database_path, database_name)
    # ************************************************************************************


    # ************************************************************************************
    def ensure_database_exists(self):
        """Ensures that the database file exists and has been merged, then opens the connection"""
        if not exists(self._database_full_path):
            if self._database_splits_exist():
                self._merge_database()
                if not exists(self._database_full_path):
                    print('\n******************************')
                    print('Unable to merge database file!')
                    print('******************************\n')
                    exit()
            else:
                print('\n******************************')
                print('Database split-files not found!')
                print('******************************\n')
                exit()

        self._open_connection()
    # ************************************************************************************


    # ************************************************************************************
    def select(self, select_query: str, params: tuple = ()):
        """Select data from the local database"""
        if not self._conn:
            return []
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute(select_query, params)
                rows = cursor.fetchall()
                cursor.close()
                return rows
        except Error:
            return []
    # ************************************************************************************


    # ************************************************************************************
    def _extract_game_cover_blob(self, row_id, image_out_path: str):
        """Extract the game cover art data from the local database"""
        if not self._conn:
            return
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute('SELECT psio FROM covers WHERE id = ?', (row_id,))
                image_blob = cursor.fetchone()
                cursor.close()
            if image_blob:
                with open(image_out_path, 'wb') as output_file:
                    output_file.write(image_blob[0])
        except Error:
            pass
    # ************************************************************************************


    # ************************************************************************************
    def _extract_game_libcrypt_patch_blob(self, row_id, ppf_out_path: str):
        """Extract the game LibCrypt PPF patch data from the local database"""
        if not self._conn:
            return
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute('SELECT psio FROM libcrypt_patches WHERE id = ?', (row_id,))
                patch_blob = cursor.fetchone()
                cursor.close()
            if patch_blob:
                with open(ppf_out_path, 'wb') as output_file:
                    output_file.write(patch_blob[0])
        except Error:
            pass
    # ************************************************************************************


    # ************************************************************************************
    def get_game_data(self, game_id: str) -> dict:
        """Get disc_number, collection and libcrypt status in a single query"""
        if not game_id:
            return {}
        formatted_game_id = game_id.replace('-', '_')
        response = self.select(
            'SELECT disc_number, collection, libcrypt FROM games WHERE game_id = ?',
            (formatted_game_id,)
        )
        if response:
            row = response[0]
            return {
                'disc_number': row[0] or 0,
                'collection': row[1] or '',
                'libcrypt': bool(row[2])
            }
        return {}

    def get_database_disc_collection(self, game_id: str) -> str:
        """Get the game collection from the local database"""
        if not game_id:
            return ''

        formatted_game_id = game_id.replace('-', '_')
        response = self.select(
            'SELECT collection FROM games WHERE game_id = ?',
            (formatted_game_id,)
        )
        return response[0][0] if response else ''
    # ************************************************************************************


    # ************************************************************************************
    def get_redump_name(self, game_id: str) -> str:
        """Get game name from Redump/PSX Data-Centre stored in local database"""
        if not game_id:
            return ''

        formatted_game_id = game_id.replace('-', '_')
        response = self.select(
            'SELECT name FROM games WHERE game_id = ?',
            (formatted_game_id,)
        )
        return response[0][0] if response else ''
    # ************************************************************************************


    # ************************************************************************************
    def get_track_info(self, game_id: str):
        """Get disc track info from the local database"""
        if not game_id:
            return

        formatted_game_id = game_id.replace('-', '_')
        return self.select(
            'SELECT track_number, pregap, sectors, size, crc '
            'FROM tracks '
            'WHERE game_id = ? '
            'ORDER BY track_number',
            (formatted_game_id,)
        )
    # ************************************************************************************


    # ************************************************************************************
    def get_database_disc_number(self, game_id: str):
        """Get disc number from the local database"""
        if not game_id:
            return

        formatted_game_id = game_id.replace('-', '_')
        response = self.select(
            'SELECT disc_number FROM games WHERE game_id = ?',
            (formatted_game_id,)
        )
        return response[0][0] if response else 0
    # ************************************************************************************


    # ************************************************************************************
    def get_libcrypt_status(self, game_id: str):
        """Get libcrypt status from local database"""
        if not game_id:
            return

        formatted_game_id = game_id.replace('-', '_')
        response = self.select(
            'SELECT libcrypt FROM games WHERE game_id = ?',
            (formatted_game_id,)
        )
        return response[0][0] if response else 0
    # ************************************************************************************


    # ************************************************************************************
    def libcrypt_patch_available(self, game_id: str) -> bool:
        """Check if LibCrypt PPF patch is available in local database"""
        if not game_id:
            return False

        formatted_game_id = game_id.replace('-', '_')
        response = self.select(
            'SELECT id FROM libcrypt_patches WHERE game_id = ?',
            (formatted_game_id,)
        )
        return bool(response)
    # ************************************************************************************


    # ************************************************************************************
    def copy_game_cover(self, output_path: str, game_id: str, game_name: str) -> bool:
        """Copy game front cover art from the database. Returns True if copied."""
        if not game_id or not self._conn:
            return False
        formatted_game_id = game_id.replace('-', '_')
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute('SELECT psio FROM covers WHERE game_id = ?', (formatted_game_id,))
                row = cursor.fetchone()
                cursor.close()
            if row:
                with open(join(output_path, f'{game_name}.bmp'), 'wb') as f:
                    f.write(row[0])
                return True
        except Error:
            pass
        return False
    # ************************************************************************************


    # ************************************************************************************
    def copy_libcrypt_patch(self, output_path: str, game_id: str) -> bool:
        """Copy LibCrypt PPF patch from the database. Returns True if copied."""
        if not game_id or not self._conn:
            return False
        formatted_game_id = game_id.replace('-', '_')
        try:
            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute('SELECT psio FROM libcrypt_patches WHERE game_id = ?', (formatted_game_id,))
                row = cursor.fetchone()
                cursor.close()
            if row:
                with open(join(output_path, f'{game_id}.ppf'), 'wb') as f:
                    f.write(row[0])
                return True
        except Error:
            pass
        return False
    # ************************************************************************************