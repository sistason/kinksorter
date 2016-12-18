#!/usr/bin/env python3

import os
import subprocess
from database import Database
from movie import Movie

class KinkSorter():

    def __init__(self, storage_root_path):
        self.storage_root_path = storage_root_path
        database_path = path.join(self.storage_root_path, '.kinksorter_db')
        self.database = Database(database_path)

    def update_database(self):
        self._scan_directory(self.storage_root_path, 10)

    def _scan_directory(self, dir_, recursion_depth):
        recursion_depth -= 1
        for entry in os.scandir(dir_):
            full_path = os.path.join(self.storage_root_path, dir_, entry.path)
            if entry.is_file() or entry.is_symlink():
                if os.access(full_path, os.R_OK):
                    mime_type = subprocess.check_output(['file', '-b', '--mime-type', full_path])
                    if mime_type and mime_type.decode('utf-8').startswith('video/'):
                        self.database.add_movie(Movie(full_path))
            if entry.is_dir():
                if recursion_depth > 0:
                    self._scan_directory(full_path, recursion_depth)

    def sort(self):
        ...

if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('%s is no directory or isn\'t writeable' % string)

    argparser = argparse.ArgumentParser(description="Easy Kink storage structuring")

    argparser.add_argument('storage_root_path', type=argcheck_dir,
                           help='Set the root path of the storage')
    argparser.add_argument('--schema', '-s', type=str,
                           help='Restructure to given schema')

    args = argparser.parse_args()

    m = KinkSorter(args.storage_root_path)
    m.update_database()

    if args.schema:
        m.sort(args.schema)
