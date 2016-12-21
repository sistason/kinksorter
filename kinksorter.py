#!/usr/bin/env python3

import os
import shutil
import subprocess
from database import Database
from movie import Movie
from api import KinkAPI


class KinkSorter():

    def __init__(self, storage_root_path):
        self.storage_root_path = storage_root_path
        self.api = KinkAPI()
        database_path = path.join(self.storage_root_path, '.kinksorter_db')
        self.database = Database(database_path, self.api)
        self.database.read()

    def update_database(self):
        self._scan_directory(self.storage_root_path, 10)
        self.database.write()

    def _scan_directory(self, dir_, recursion_depth):
        recursion_depth -= 1
        for entry in os.scandir(dir_):
            full_path = os.path.join(self.storage_root_path, dir_, entry.path)
            if entry.is_file() or entry.is_symlink():
                if os.access(full_path, os.R_OK):
                    mime_type = subprocess.check_output(['file', '-b', '--mime-type', full_path])
                    if mime_type and mime_type.decode('utf-8').startswith('video/'):
                        self.database.add_movie(Movie(full_path, self.api))
            if entry.is_dir():
                if recursion_depth > 0:
                    self._scan_directory(full_path, recursion_depth)

    def sort(self, simulation=True):
        storage_path, old_storage_name = self.storage_root_path.rsplit('/',1)
        new_storage_path = os.path.join(storage_path, old_storage_name+'_kinksorted_0')
        while os.path.exists(new_storage_path):
            p_, cnt_  = new_storage_path.rsplit('_',1)
            new_storage_path = p_ + '_' + str(int(cnt_)+1) if cnt_.isdigit() else p_ + '_0'
        os.mkdir(new_storage_path)
        for path, movie in self.database.movies.items():
            new_site_path = os.path.join(new_storage_path, movie.properties['site'])
            if not os.path.exists(new_site_path):
                os.mkdir(new_site_path)

            if movie:
                new_movie_path = os.path.join(new_storage_path, str(movie)+movie.extension)
            else:
                new_movie_path = os.path.join(new_storage_path, 'unsorted', str(movie) + movie.extension)

            if simulation:
                os.symlink(path, new_movie_path)
            else:
                shutil.move(path, new_movie_path)

        ...

if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('%s is no directory or isn\'t writeable' % string)

    argparser = argparse.ArgumentParser(description="Easy Kink storage renaming/structuring")

    argparser.add_argument('storage_root_path', type=argcheck_dir,
                           help='Set the root path of the storage')
    argparser.add_argument('-t', '--', type=bool,
                           help="Sort/rename movies only by simulating it with symlinks in ./_test_kinksorter/")

    args = argparser.parse_args()

    m = KinkSorter(args.storage_root_path)
    m.update_database()
    m.sort(simulation=args.test)