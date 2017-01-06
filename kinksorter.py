#!/usr/bin/env python3

import logging
import os
import re
import shutil
import subprocess

from database import Database
from movie import Movie
import utils


class KinkSorter():
    settings = None

    def __init__(self, storage_root_path, settings):
        logging.basicConfig(format='%(message)s', level=logging.INFO)

        self.storage_root_path = storage_root_path
        self.settings = settings
        Movie.settings = settings

        database_path = path.join(self.storage_root_path, '.kinksorter_db')
        self.database = Database(database_path, self.settings)
        self.database.read()

    def update_database(self):
        old_db_len_ = len(self.database.movies)
        self._scan_directory(self.storage_root_path, self.settings.RECURSION_DEPTH)
        self.database.write()

        new_db_len_ = len(self.database.movies)
        logging.info('{} movies found, {} new ones'.format(new_db_len_, new_db_len_-old_db_len_))
        try:
            self.database.update_all_movies()
        except KeyboardInterrupt as e:
            logging.info('Saving Database and exiting...')
            self.database.write()

        self.database.write()

    def _scan_directory(self, dir_, recursion_depth=0):
        recursion_depth -= 1
        for entry in os.scandir(dir_):
            full_path = os.path.join(self.storage_root_path, dir_, entry.path)
            if entry.is_file() or entry.is_symlink():
                logging.debug('\tScanning file {}...'.format(entry.path))
                if os.access(full_path, os.R_OK):
                    mime_type = subprocess.check_output(['file', '-b', '--mime-type', full_path])
                    if mime_type and mime_type.decode('utf-8').startswith('video/'):
                        logging.debug('\tAdding movie {}...'.format(entry.path))
                        m_ = Movie(full_path, api=self._current_site_api)
                        self.database.add_movie(m_)
            if entry.is_dir():
                if recursion_depth == self.settings.RECURSION_DEPTH - 1:
                    self._current_site_api = utils.get_correct_api(self.settings.apis, entry.name)
                    name_ = self._current_site_api.name if self._current_site_api else '<None>'
                    logging.info('Scanning site-directory (API: {}) {}...'.format(name_, entry.path))

                if recursion_depth > 0:
                    self._scan_directory(full_path, recursion_depth)

    def sort(self):
        storage_path, old_storage_name = os.path.split(self.storage_root_path)
        new_storage_path = os.path.join(storage_path, old_storage_name + '_kinksorted')
        if self.settings.simulation:
            new_storage_path += '_0'
            while os.path.exists(new_storage_path):
                p_, cnt_ = new_storage_path.rsplit('_',1)
                new_storage_path = p_ + '_' + str(int(cnt_)+1) if cnt_.isdigit() else p_ + '_0'
        if not os.path.exists(new_storage_path):
            os.mkdir(new_storage_path)

        for old_movie_path, movie in self.database.movies.items():
            if not os.path.exists(old_movie_path) or os.access(old_movie_path, os.R_OK):
                continue
            site_ = movie.properties['site'] if 'site' in movie.properties and movie.properties['site'] else 'unsorted'
            new_site_path = os.path.join(new_storage_path, site_)
            if not os.path.exists(new_site_path):
                os.mkdir(new_site_path)

            new_movie_path = os.path.join(new_site_path, str(movie))

            if os.path.exists(new_movie_path):
                # Duplicate! Keep the one with bigger file size ;)
                old_movie_size_ = os.stat(new_movie_path).st_size
                new_movie_size_ = os.stat(movie.file_path).st_size
                if old_movie_size_ >= new_movie_size_:
                    logging.debug('"{}" was duplicate of "{}", but was smaller and is therefore skipped'.format(
                        movie, new_movie_path))
                    continue
                os.remove(new_movie_path)

            self._move_movie(old_movie_path, new_movie_path)

    def _move_movie(self, old_movie_path, new_movie_path):
        if re.match(r'https?://|ftps?://', old_movie_path):
            if self.settings.simulation:
                self.database.merge_diff_list.append((old_movie_path, new_movie_path))
            else:
                file_ = utils.get_remote_file(old_movie_path)
                if file_ is not None and os.path.exists(file_):
                    shutil.move(file_, new_movie_path)
        else:
            if self.settings.simulation:
                os.symlink(old_movie_path, new_movie_path)
                self.database.merge_diff_list.append((old_movie_path, new_movie_path))
            else:
                shutil.move(old_movie_path, new_movie_path)

    def revert(self):
        storage_path, old_storage_name = os.path.split(self.storage_root_path)
        sorted_path = os.path.join(storage_path, old_storage_name + '_kinksorted')

        n = len(self.database.movies)
        for i, (path_, movie) in enumerate(self.database.movies.items()):
            if os.path.exists(path_):
                continue
            movie_name = str(movie)
            site_ = movie.properties['site'] if 'site' in movie.properties and movie.properties['site'] else 'unsorted'
            sorted_site_path = os.path.join(sorted_path, site_)
            sorted_movie_path = os.path.join(sorted_site_path, movie_name)
            if os.path.exists(sorted_movie_path):
                if re.match(r'https?://|ftps?://', path_):
                    logging.info('Movie "{}" came from read-only storage'.format(movie_name))
                    new_ro_dir = os.path.join(storage_path, 'from_read-only')
                    if not os.path.exists(new_ro_dir):
                        os.mkdir(new_ro_dir)
                    new_ro_site_dir = os.path.join(new_ro_dir, site_)
                    if not os.path.exists(new_ro_site_dir):
                        os.mkdir(new_ro_site_dir)
                    shutil.move(sorted_movie_path, os.path.join(new_ro_site_dir, movie_name))
                else:
                    shutil.move(sorted_movie_path, path_)

            logging.info('Reverted movie "{}"... ({}/{})'.format(movie_name, i + 1, n))

    def merge(self, merge_dir):
        self._scan_merge_dir(merge_dir)



        # sort

    def _scan_merge_dir(self, address):
        """ Add all movies at the address to the database """
        if re.match(r'ftps?://', address):
            listing = utils.get_ftp_listing(address)
            for path_, (name_, facts) in listing.items():
                full_path = os.path.join(path_, name_)
                # TODO
#                self._current_site_api = utils.get_correct_api(self.settings.apis, path_)
#                name_ = self._current_site_api.name if self._current_site_api else '<None>'
#                logging.info('Scanning site-directory (API: {}) {}...'.format(name_, entry.path))

#                if ("media-type" in facts and "video/" != facts["media-type"]
#                    or "perm" in facts): # TODO: facts['perm'] == fitting

#                    logging.debug('\tAdding movie {}...'.format(full_path))
#                    m_ = Movie(full_path, api=self._current_site_api)
#                    self.database.add_movie(m_)


#                if recursion_depth > 0:
#                    self._scan_directory(full_path, recursion_depth)

        elif re.match(r'https?://', address):
            listing = utils.get_http_listing(address)
            for path_, (name_, facts) in listing.items():
                full_path = os.path.join(path_, name_)
                # TODO

        else:
            self._scan_directory(address, self.settings.RECURSION_DEPTH)


if __name__ == '__main__':
    import argparse
    from os import path, access, W_OK, R_OK

    def argcheck_dir(string):
        if path.isdir(string) and access(string, W_OK) and access(string, R_OK):
            return path.abspath(string)
        raise argparse.ArgumentTypeError('%s is no directory or isn\'t writeable' % string)

    argparser = argparse.ArgumentParser(description="Easy Kink storage renaming/structuring")

    argparser.add_argument('storage_root_path', type=argcheck_dir,
                           help='Set the root path of the storage, has to be a writeable directory')
    argparser.add_argument('merge_paths', nargs='*',
                           help='Merge (Copy) given storage(s) into the root-storage.')

    argparser.add_argument('-t', '--tested', action="store_true",
                           help="Move movies instead of symlinking them")
    argparser.add_argument('-i', '--interactive', action="store_true",
                           help="Confirm each movie and query fails manually")
    argparser.add_argument('-r', '--revert', action="store_true",
                           help="Revert the sorted movies back to their original state when first run (implies -t)")
    argparser.add_argument('-s', '--shootid_template', default='templates/shootid.jpeg',
                           help="Set the template-image for finding the Shoot ID")

    args = argparser.parse_args()

    settings = utils.Settings(vars(args))
    m = KinkSorter(args.storage_root_path, settings)

    logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                        level=logging.INFO)
    logging.basicConfig()
    if args.revert:
        m.revert()
    else:
        m.update_database()
        m.sort()
        if args.merge_paths:
            m.merge(args.merge_paths)
