#!/usr/bin/env python3

import os
import shutil
import subprocess
import logging

from database import Database
from movie import Movie
from api import KinkAPI


class KinkSorter():
    settings = {}

    def __init__(self, storage_root_path, interactive):
        logging.basicConfig(format='%(message)s', level=logging.INFO)

        self.storage_root_path = storage_root_path
        self.settings['interactive'] = interactive
        self.settings['api'] = KinkAPI()
        database_path = path.join(self.storage_root_path, '.kinksorter_db')
        self.database = Database(database_path, self.settings)
        self.database.read()

    def update_database(self):
        old_db_size_ = len(self.database.movies)
        self._scan_directory(self.storage_root_path, 10)
        self.database.write()

        new_db_size_ = len(self.database.movies)
        logging.info('{} movies found, {} new ones'.format(new_db_size_, new_db_size_-old_db_size_))

        self.database.update_all_movies()
        self.database.write()

    def _scan_directory(self, dir_, recursion_depth):
        recursion_depth -= 1
        for entry in os.scandir(dir_):
            full_path = os.path.join(self.storage_root_path, dir_, entry.path)
            if entry.is_file() or entry.is_symlink():
                logging.debug('\tScanning file {}...'.format(entry.path))
                if os.access(full_path, os.R_OK):
                    mime_type = subprocess.check_output(['file', '-b', '--mime-type', full_path])
                    if mime_type and mime_type.decode('utf-8').startswith('video/'):
                        logging.debug('\tAdding movie {}...'.format(entry.path))
                        m_ = Movie(full_path, self.settings)
                        self.database.add_movie(m_)
            if entry.is_dir():
                if recursion_depth > 0:
                    if recursion_depth == 9:
                        logging.info('Scanning directory {}...'.format(entry.path))
                    self._scan_directory(full_path, recursion_depth)

    def sort(self, simulation=True):
        storage_path, old_storage_name = self.storage_root_path.rsplit('/',1)
        new_storage_path = os.path.join(storage_path, old_storage_name+'_kinksorted_0')
        while os.path.exists(new_storage_path):
            p_, cnt_ = new_storage_path.rsplit('_',1)
            new_storage_path = p_ + '_' + str(int(cnt_)+1) if cnt_.isdigit() else p_ + '_0'
        os.mkdir(new_storage_path)
        for old_movie_path, movie in self.database.movies.items():
            new_site_path = os.path.join(new_storage_path, movie.properties.get('site', 'unsorted'))
            if not os.path.exists(new_site_path):
                os.mkdir(new_site_path)

            new_movie_path = os.path.join(new_site_path, str(movie) + '.' + movie.extension)

            if os.path.exists(new_movie_path):
                # Duplicate! Keep the one with bigger file size ;)
                old_movie_size_ = os.stat(new_movie_path).st_size
                new_movie_size_ = os.stat(movie.file_path).st_size
                if old_movie_size_ >= new_movie_size_:
                    logging.debug('"{}" was duplicate of "{}", but was smaller and is therefore skipped'.format(
                        movie, new_movie_path))
                    continue
                os.remove(new_movie_path)

            if simulation:
                os.symlink(old_movie_path, new_movie_path)
            else:
                shutil.move(old_movie_path, new_movie_path)

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
    argparser.add_argument('-t', '--tested', type=bool, default=False,
                           help="Sort/rename movies only by simulating it with symlinks in ./_test_kinksorter/")
    argparser.add_argument('-i', '--interactive', action="store_true",
                           help="Sort/rename movies only by simulating it with symlinks in ./_test_kinksorter/")

    args = argparser.parse_args()

    m = KinkSorter(args.storage_root_path, args.interactive)

    logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                        level=logging.INFO)
    m.update_database()
    m.sort(simulation=not args.tested)
